import numpy as np
import torch
import torch.functional as F
from torch.distributions import Categorical
from torch.distributions.normal import Normal
import math

from shiva.utils import Noise as noise
from shiva.agents.PPOAgent import PPOAgent
from shiva.algorithms.Algorithm import Algorithm

class ContinuousPPOAlgorithm(Algorithm):
    def __init__(self,obs_space, acs_space, action_space_discrete, action_space_continuous, configs):
        super(ContinuousPPOAlgorithm, self).__init__(obs_space,acs_space,configs)
        torch.manual_seed(self.configs[0]['manual_seed'])
        self.epsilon_clip = configs[0]['epsilon_clip']
        self.gamma = configs[0]['gamma']
        self.gae_lambda = configs[0]['lambda']
        self.grad_clip = configs[0]['grad_clip']
        self.policy_loss = 0
        self.value_loss = 0
        self.entropy_loss = 0
        self.loss = 0
        self.acs_space = acs_space
        self.obs_space = obs_space
        self.acs_discrete = action_space_discrete
        self.acs_continuous = action_space_continuous


    def update(self, agent,buffer, step_count):
        '''
            Getting a Batch from the Replay Buffer
        '''
        minibatch = buffer.full_buffer()
        # Batch of Experiences
        states, actions, rewards, logprobs, next_states, dones = minibatch

        # Make everything a tensor and send to gpu if available
        states = torch.tensor(states).to(self.device)
        actions = torch.tensor(actions).float().to(self.device)
        rewards = torch.tensor(rewards).to(self.device)
        next_states = torch.tensor(next_states).to(self.device)
        # done_masks = torch.tensor(dones, dtype=np.bool).to(self.device)
        done_masks = torch.ByteTensor(dones).to(self.device)
        #Calculate approximated state values and next state values using the critic
        values = agent.critic(agent.policy_base(states.float())).to(self.device)
        next_values = agent.critic(agent.policy_base(next_states.float())).to(self.device)


        #Calculate Discounted Rewards and Advantages using the General Advantage Equation
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
        advantage = torch.tensor(advantage).float()
        #Normalize the advantages
        advantage = (advantage - torch.mean(advantage)) / torch.std(advantage)

        old_log_probs = torch.from_numpy(logprobs)

        #Update model weights for a configurable amount of epochs
        for epoch in range(self.configs[0]['update_epochs']):
            agent.critic_optimizer.zero_grad()
            values = agent.critic(agent.policy_base(states.float()))
            self.value_loss = self.loss_calc(values,new_rewards.unsqueeze(dim=-1))
            self.value_loss.backward()
            agent.critic_optimizer.step()


            agent.actor_optimizer.zero_grad()
            mu_new = agent.mu(agent.policy_base(states.float()))
            sigma_new = torch.sqrt(agent.var(agent.policy_base(states.float())))
            #log_std = agent.log_std.expand_as(mu_new)
            #cov_mat = torch.diag(agent.var)
            dist2 = Normal(mu_new,sigma_new)
            new_log_probs = dist2.log_prob(actions)
            entropy = dist2.entropy().sum(-1).mean()

            penalty = (dist2.cdf(-1) + 1 - dist2.cdf(1)).mean().requires_grad_(True)
            #new_log_probs = self.log_probs(mu_new,var_new,actions).float()
            ratios = torch.exp(new_log_probs.double() - old_log_probs.double()).float()
            surr1 = ratios * advantage.unsqueeze(dim=-1)
            surr2 = torch.clamp(ratios,1.0-self.epsilon_clip,1.0+self.epsilon_clip) * advantage.unsqueeze(dim=-1)
            #entropy = (torch.logs(2*math.pi*var_new) +1)/2
            self.entropy_loss = -(self.configs[0]['beta']*entropy)
            self.policy_loss =  -torch.min(surr1,surr2).mean() + penalty + self.entropy_loss
            self.policy_loss.backward()
            #torch.nn.utils.clip_grad_norm(agent.optimizer.parameters(), self.grad_clip)
            agent.actor_optimizer.step()

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
        self.agent = PPOAgent(self.id_generator(), self.obs_space, self.acs_discrete, self.acs_continuous, self.configs[1], self.configs[2])
        return self.agent

    def __str__(self):
        return 'ContinuousPPOAlgorithm'