from settings import shiva
from .Learner import Learner
import helpers.misc as misc
import torch.multiprocessing as mp
import envs
import algorithms
import buffers
import copy
import random
import numpy as np

class SingleAgentPPOLearner(Learner):
    def __init__(self, learner_id, config):
        super(SingleAgentPPOLearner,self).__init__(learner_id, config)

    def run(self):
        self.step_count = 0
        for self.ep_count in range(self.episodes):
            self.env.reset()
            self.totalReward = 0
            done = False
            while not done:
                done = self.step()
                self.step_count +=1
            if self.step_count % self.configs['Algorithm']['update_steps'] >= 1:
                self.alg.update(self.agent,self.buffer.full_buffer(),self.step_count)
                self.buffer.clear_buffer()

        self.env.close()


    def step(self):

        observation = self.env.get_observation()
        if self.configs['Agent']['action_space'] == 'Discrete':
            action= self.agent.get_action(observation)
        elif self.configs['Agent']['action_space'] == 'Continuous':
            action = self.agent.get_continuous_action(observation)
        next_observation, reward, done, more_data = self.env.step(action)

        # TensorBoard metrics
        shiva.add_summary_writer(self, self.agent, 'Actor_Loss_per_Step', self.alg.loss, self.step_count)
        #shiva.add_summary_writer(self, self.agent, 'Critic Loss per Step', self.alg.get_critic_loss(), self.step_count)
        shiva.add_summary_writer(self, self.agent, 'Normalized_Reward_per_Step', reward, self.step_count)
        shiva.add_summary_writer(self, self.agent, 'Raw_Reward_per_Step', more_data['raw_reward'], self.step_count)
        self.totalReward += more_data['raw_reward'][0] if type(more_data['raw_reward']) == list else more_data['raw_reward']
        t = [observation, action, reward, next_observation, int(done)]
        deep = copy.deepcopy(t)
        self.buffer.append(deep)


        # TensorBoard Metrics
        if done:
            shiva.add_summary_writer(self, self.agent, 'Total_Reward_per_Episode', self.totalReward, self.ep_count)

        return done

    def create_environment(self):
        # create the environment and get the action and observation spaces
        environment = getattr(envs, self.configs['Environment']['type'])
        return environment(self.configs['Environment'])

    def create_algorithm(self):
        algorithm = getattr(algorithms, self.configs['Algorithm']['type'])
        acs_continuous = self.env.action_space_continuous
        acs_discrete= self.env.action_space_discrete
        return algorithm(self.env.get_observation_space(), self.env.get_action_space(), acs_discrete, acs_continuous, [self.configs['Algorithm'], self.configs['Agent'], self.configs['Network']])

    def create_buffer(self):
        buffer = getattr(buffers,self.configs['Buffer']['type'])
        return buffer(self.configs['Buffer']['batch_size'], self.configs['Buffer']['capacity'])

    def get_agents(self):
        return self.agents

    def get_algorithm(self):
        return self.alg

    def launch(self):

        # Launch the environment
        self.env = self.create_environment()

        # Launch the algorithm which will handle the
        self.alg = self.create_algorithm()
        # Create the agent
        if self.load_agents:
            self.agent= self.load_agent(self.load_agents)
        else:
            self.agent= self.alg.create_agent()


        # if buffer set to true in config
        if self.using_buffer:
            # Basic replay buffer at the moment
            self.buffer = self.create_buffer()

        print('Launch Successful.')


    def save_agent(self):
        pass

    def load_agent(self, path):
        return shiva._load_agents(path)[0]
