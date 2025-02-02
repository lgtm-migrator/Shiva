import numpy as np
import random
import copy
import torch

from shiva.core.admin import Admin
from shiva.learners.Learner import Learner
from shiva.helpers.config_handler import load_class

class SingleAgentDQNLearner(Learner):
    def __init__(self, learner_id, config):
        super(SingleAgentDQNLearner,self).__init__(learner_id, config)

    def run(self, train=True):
        step_count_per_run = 0
        while not self.env.finished(self.episodes):
            self.env.reset()
            while not self.env.is_done():
                self.step()
                self.collect_metrics() # metrics per step
                # print('LEARNER {}\tStep {}\tSessionSteps: {}\tDones: {}\tReward: {}'.format(self.id, self.env.steps_per_episode, self.env.step_count, self.env.done_count, self.env.reward_per_step))

                ''' FOR MULTIPROCESS PBT PURPOSES '''
                self.step_count = self.env.step_count
                self.ep_count = self.env.done_count
                try:
                    if self.multi and step_count_per_run >= self.updates_per_iteration:
                        return None
                except:
                    pass
                step_count_per_run += 1
                ''''''
            self.alg.update(self.agent, self.buffer, self.env.step_count)
            self.collect_metrics(True) # metrics per episode
            self.checkpoint()
            # print('Learner {}\tEpisode {} complete on {} steps!\tEpisodic reward: {} '.format(self.id, self.ep_count, self.env.steps_per_episode, self.env.reward_per_episode))

        self.env.close()

    def step(self):
        observation = self.env.get_observation()
        """Temporary fix for Unity as it receives multiple observations"""
        if len(observation.shape) > 1:
            action = [self.agent.get_action(obs, self.step_count) for obs in observation]
            next_observation, reward, done, more_data = self.env.step(action)
            z = copy.deepcopy(zip(observation, action, reward, next_observation, done))
            for obs, act, rew, next_obs, don in z:
                # exp = [obs, act, rew, next_obs, int(don)]
                exp = list(map(torch.clone, (torch.tensor(observation), torch.tensor(action), torch.tensor(reward), torch.tensor(next_observation), torch.tensor([done], dtype=torch.bool))))
                # print(act, rew, don)
                self.buffer.push(exp)
        else:
            action = self.agent.get_action(observation, self.step_count)
            next_observation, reward, done, more_data = self.env.step(action)
            t = [observation, action, reward, next_observation, int(done)]
            # exp = copy.deepcopy(t)
            exp = list(map(torch.clone, (torch.tensor(observation), torch.tensor(action), torch.tensor(reward), torch.tensor(next_observation), torch.tensor([done], dtype=torch.bool))))
            self.buffer.push(exp)
        """"""

    def create_algorithm(self):
        algorithm_class = load_class('shiva.algorithms', self.configs['Algorithm']['type'])
        try:
            self.configs['Agent']['learning_rate'] = random.uniform(self.learning_rate[0],self.learning_rate[1])
            return algorithm_class(self.env.get_observation_space(), self.env.get_action_space(), self.configs)
        except:
            return algorithm_class(self.env.get_observation_space(), self.env.get_action_space(), self.configs)

    def create_buffer(self):
        # SimpleBuffer
        # buffer_class = load_class('shiva.buffers', self.configs['Buffer']['type'])
        # return buffer_class(self.configs['Buffer']['batch_size'], self.configs['Buffer']['capacity'])
        # TensorBuffer
        buffer_class = load_class('shiva.buffers', self.configs['Buffer']['type'])
        return buffer_class(self.configs['Buffer']['capacity'], self.configs['Buffer']['batch_size'], 1, self.env.get_observation_space(), self.env.get_action_space()['acs_space'])


    def launch(self):
        self.env = self.create_environment()

        self.alg = self.create_algorithm()

        if self.load_agents:
            self.agent = Admin._load_agent(self.load_agents)
            self.buffer = Admin._load_buffer(self.load_agents)
        else:
            self.agent = self.alg.create_agent(self.get_new_agent_id())
            if self.using_buffer:
                self.buffer = self.create_buffer()

        print('Launch Successful.')
