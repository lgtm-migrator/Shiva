import numpy as np
import torch
import torch.functional as F
import utils.Noise as noise
from torch.nn import Softmax as Softmax
from agents.PPOAgent import PPOAgent
from .Algorithm import Algorithm
from torch.distributions import Categorical
import copy


class PPOAlgorithm(Algorithm):
    def __init__(self,obs_space, acs_space, action_space_discrete, action_space_continuous, configs):

        super(PPOAlgorithm, self).__init__(obs_space,acs_space,configs)
        torch.manual_seed(self.configs[0]['manual_seed'])
        self.epsilon_clip = configs[0]['epsilon_clip']
        self.gamma = configs[0]['gamma']
        self.gae_lambda = configs[0]['lambda']
        self.policy_loss = 0
        self.value_loss = 0
        self.entropy_loss = 0
        self.loss = 0
        self.acs_space = acs_space
        self.obs_space = obs_space
        self.acs_discrete = action_space_discrete
        self.acs_continuous = action_space_continuous
        self.softmax = Softmax(dim=-1)


    def update(self, agent,old_agent,buffer, step_count):
        '''
            Getting a Batch from the Replay Buffer
        '''
        self.step_count = step_count
        minibatch = buffer.full_buffer()

        # Batch of Experiences
        states, actions, rewards, next_states, dones = minibatch

        # Make everything a tensor and send to gpu if available
        states = torch.tensor(states).to(self.device)
        actions = torch.tensor(np.argmax(actions, axis=-1)).to(self.device).long()
        rewards = torch.tensor(rewards).to(self.device)
        next_states = torch.tensor(next_states).to(self.device)
        done_masks = torch.ByteTensor(dones).to(self.device)
        #Calculate approximated state values and next state values using the critic
        values = agent.critic(states.float()).to(self.device)
        next_values = agent.critic(states.float()).to(self.device)


        new_rewards = []
        advantage = []
        delta= 0
        gae = 0
        for i in reversed(range(len(rewards))):
            if done_masks[i]:
                delta = rewards[i]-values[i]
                gae = delta
            else:
                delta = rewards[i] + self.gamma * next_values[i]  - values[i]
                gae = delta + self.gamma * self.gae_lambda * gae
            new_rewards.insert(0,gae+values[i])
            advantage.insert(0,gae)
        #Format discounted rewards and advantages for torch use
        new_rewards = torch.tensor(new_rewards).float().to(self.device)
        advantage = torch.tensor(advantage).float().to(self.device)
        #Normalize the advantages
        advantage = (advantage - torch.mean(advantage)) / torch.std(advantage)
        #Calculate log probabilites of the old policy for the policy objective
        old_action_probs = old_agent.actor(states.float())
        dist = Categorical(old_action_probs)
        old_log_probs = dist.log_prob(actions)

        #Update model weights for a configurable amount of epochs
        for epoch in range(self.configs[0]['update_epochs']):

            #Calculate Discounted Rewards and Advantages using the General Advantage Equation

            #Calculate log probabilites of the new policy for the policy objective
            current_action_probs = agent.actor(states.float())
            dist2 = Categorical(current_action_probs)
            log_probs = dist2.log_prob(actions)
            #Use entropy to encourage further exploration by limiting how sure
            #the policy is of a particular action
            entropy = dist2.entropy()
            #Find the ratio (pi_new / pi_old)
            ratios = torch.exp(log_probs - old_log_probs.detach())
            #Calculate objective functions
            surr1 = ratios * advantage
            surr2 = torch.clamp(ratios,1.0-self.epsilon_clip,1.0+self.epsilon_clip) * advantage
            #Zero Optimizer, Calculate Losses, Backpropagate Gradients
            agent.optimizer.zero_grad()
            self.policy_loss = -torch.min(surr1,surr2).mean()
            self.entropy_loss = -(self.configs[0]['beta']*entropy).mean()
            self.value_loss = self.loss_calc(values, new_rewards.unsqueeze(dim=-1))
            self.loss = self.policy_loss + self.value_loss + self.entropy_loss
            self.loss.backward(retain_graph = True)
            agent.optimizer.step()
        print('Done updating')
        buffer.clear_buffer()


    def get_metrics(self, episodic=False):
        if not episodic:
            metrics = [
                ('Algorithm/Loss_per_Step', self.loss),
                ('Algorithm/Policy_Loss_per_Step', self.policy_loss),
                ('Algorithm/Value_Loss_per_Step', self.value_loss),
                ('Algorithm/Entropy_Loss_per_Step', self.entropy_loss),
            ]
        else:
            metrics = []
        return metrics

    def get_actor_loss(self):
        return self.actor_loss

    def get_loss(self):
        return self.loss

    def get_critic_loss(self):
        return self.critic_loss

    def create_agent(self):
        self.agent = PPOAgent(self.id_generator(), self.obs_space, self.acs_discrete, self.acs_continuous, self.configs[1],self.configs[2])
        return self.agent
