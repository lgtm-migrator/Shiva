from .Environment import Environment
from shiva.helpers.config_handler import load_class
import numpy as np
import torch
import torch.multiprocessing as mp
from torch.distributions import Categorical
from torch.distributions.normal import Normal
import copy
import time
import os

class MultiGymWrapper(Environment):
    def __init__(self,configs,queue,agent,episode_count,agent_dir,total_episodes, saveLoadFlag, waitForLearner):
        super(MultiGymWrapper,self).__init__(configs)
        self.queue = queue
        self.agent = agent
        self.process_list = list()
        self.episode_count = episode_count
        self.total_episodes = total_episodes
        self.step_count = 0
        self.configs = configs
        self.agent_dir = agent_dir
        self.saveLoadFlag = saveLoadFlag
        self.waitForLearner = waitForLearner
        self.process_list = []
        self.envs = []
        self.p = mp.Process(target = self.launch_envs)
        self.p.start()




    def step_without_log_probs(self):

        loaded = False

        while(self.stop_collecting.item() == 0):

            # print("Wrapper Flag:",self.saveLoadFlag.item())
            # time.sleep(0.06)

            # if self.saveLoadFlag.item() == 0:
                # if self.episode_count % 5 == 0:
                    # start_time = time.time()

                # print("Gym Wrapper:",self.agent_dir)
                # self.agent.load(self.agent_dir)
                # os.system("rm -rf {}".format(self.agent_dir + '/actor.pth'))
                # print("--- %s seconds ---" % (time.time() - start_time))
                # print("Agent Loaded")

                # self.saveLoadFlag[0] = 1
                # time.sleep(0.3)
                # self.stop_collecting 

            if not loaded:
                # if self.episode_count % self.agent_update_episodes == 0 and self.episode_count != 0:
                if self.episode_count % 5 == 0 and self.episode_count != 0: 
                    loaded = True
                    if self.saveLoadFlag.item() == 0:
                        self.agent.load(self.agent_dir)
                        print("Agent Loaded")
                        self.saveLoadFlag[0] = 1
                    # time.sleep(0.1)

            if self.episode_count % self.agent_update_episodes != 0:
                loaded = False

            if self.step_control.sum().item() == self.num_instances:
                actions = self.agent.get_action(self.observations, self.step_count)
                self.observations[:,0:self.envs[0].action_space['acs_space']] = actions
                self.step_control.fill_(0)

            if self.episode_count == self.total_episodes:
                self.stop_collecting[0] = 1


        for env in self.envs:
            env.close()

        for p in self.process_list:
            p.join()

        del(self.process_list)

    def step_with_logprobs(self):

        loaded = False

        while(self.stop_collecting.item() == 0):

            if not loaded:
                if self.episode_count % self.agent_update_episodes == 0 and self.episode_count != 0:
                    loaded = True
                    self.agent.load(self.agent_dir)
                    time.sleep(0.3)

            if self.episode_count % self.agent_update_episodes != 0:
                loaded = False

            if self.step_control.sum().item() == self.num_instances:
                observations = self.observations
                action_probs = self.agent.actor(observations.to(self.device))
                actions = torch.tensor([self.agent.get_action(obs) for obs in observations.numpy()])
                if self.action_space == 'discrete':
                    actions_temp = torch.argmax(actions, dim=-1).long().to(self.device)
                    logprobs = Categorical(action_probs).log_prob(actions_temp).to(self.device)
                self.observations[:,0:self.envs[0].action_space['acs_space']] = actions

                self.log_probs[:,0] = logprobs
                self.step_control.fill_(0)

            if self.episode_count == self.total_episodes:
                self.stop_collecting[0] = 1


        for env in self.envs:
            env.close()

        for p in self.process_list:
            p.join()

        del(self.process_list)


    def launch_envs(self):
        environment = load_class('shiva.envs', self.configs['sub_type'])
        #list of the environments to be used for episode collection
        self.envs = [environment(self.configs)] * self.num_instances
        #Shared tensor will be used for communication between environment wrapper process and individual environment processes
        self.observations = torch.zeros(self.num_instances, max(self.envs[0].observation_space,self.envs[0].action_space['acs_space'])).share_memory_()
        #Shared tensor will let control data flow through the tensor
        # 0 signals env to process, 1 signals multi wrapper to process
        self.step_control = torch.zeros(self.num_instances).share_memory_()
        #Shared tensor will signal to the envs when to stop collecting episodes
        self.stop_collecting = torch.zeros(1).share_memory_()
        self.done_count = 0
        if self.logprobs:
            self.log_probs = torch.zeros(self.num_instances, 1).share_memory_()
            self.process_list = launch_processes(self.envs, self.observations, self.step_control, self.stop_collecting, self.waitForLearner, self.queue, self.max_episode_length, logprobs=self.log_probs, num_instances=self.num_instances)
            self.step_with_logprobs()
        else:
            self.process_list = launch_processes(self.envs, self.observations, self.step_control, self.stop_collecting,self.waitForLearner,self.queue, self.max_episode_length,num_instances=self.num_instances)
            self.step_without_log_probs()

def process_target(env,observations,step_control,stop_collecting, waitForLearner, id, queue,max_ep_length):
    step_count = 1
    observation_space = env.observation_space
    action_space = env.action_space['acs_space']
    ep_observations = np.zeros((max_ep_length,observation_space))
    ep_actions= np.zeros((max_ep_length,action_space))
    ep_rewards= np.zeros((max_ep_length,1))
    ep_next_observations= np.zeros((max_ep_length,observation_space))
    ep_dones= np.zeros((max_ep_length,1))
    idx = 0
    env.reset()
    observation = env.get_observation()
    observations[id] = torch.tensor(observation).float()
    step_control[id] = 0
    while(stop_collecting.item() == 0):
        #print('Hello')
        #print('Process: ', step_control[id])
        if step_control[id] == 0 and waitForLearner.item() == 0:
            # time.sleep(0.06)
            action = observations[id][:action_space].numpy()
            next_observation, reward, done, more_data = env.step(action)
            ep_observations[idx] = observation
            ep_actions[idx] = more_data['action']
            ep_rewards[idx] = reward
            ep_next_observations[idx] = next_observation
            ep_dones[idx] = int(done)
            idx += 1


            '''t = [observation, action, reward, next_observation, int(done)]
            exp = copy.deepcopy(t)
            print('List: ',exp)
            print('Tensor: ', torch.tensor(exp))
            episode_trajectory[episode_index:episode_index + len(exp)] = torch.tensor(exp)
            episode_index += len(exp)'''
            if done:
                exp = copy.deepcopy(zip(ep_observations[:idx],ep_actions[:idx],ep_rewards[:idx],ep_next_observations[:idx],ep_dones[:idx]))
                queue.put(exp)
                env.reset()
                observation = env.get_observation()
                observations[id] = observation
                ep_observations.fill(0)
                ep_actions.fill(0)
                ep_rewards.fill(0)
                ep_next_observations.fill(0)
                ep_dones.fill(0)
                idx = 0
                step_control[id] = 1
            else:
                observations[id] = torch.from_numpy(next_observation)
                observation = next_observation
                step_control[id] = 1


def process_target_with_log_probs(env,observations,step_control,stop_collecting, id, queue,logprobs, max_ep_length):
# def process_target(self):
    #tensor for storing episodes per process/env
    step_count = 1
    observation_space = env.observation_space
    action_space = env.action_space['acs_space']
    ep_observations = np.zeros((max_ep_length,observation_space))
    ep_actions = np.zeros((max_ep_length,action_space))
    ep_rewards = np.zeros((max_ep_length,1))
    ep_logprobs = np.zeros((max_ep_length, action_space))
    ep_next_observations = np.zeros((max_ep_length,observation_space))
    ep_dones = np.zeros((max_ep_length,1))
    idx = 0
    env.reset()
    observation = env.get_observation()
    observations[id] = torch.tensor(observation).float()
    step_control[id] = 0

    while(stop_collecting.item() == 0):
        #print('Hello')
        #print('Process: ', step_control[id])
        if(step_control[id] == 0):
            action = observations[id][:action_space].numpy()
            log_probs = logprobs[id][0].numpy()
            next_observation, reward, done, more_data = env.step(action)
            ep_observations[idx] = observation
            ep_actions[idx] = action
            ep_rewards[idx] = reward
            ep_logprobs[idx] = log_probs
            ep_next_observations[idx] = next_observation
            ep_dones[idx] = int(done)
            idx += 1

            # print("Hello")

            '''t = [observation, action, reward, next_observation, int(done)]
            exp = copy.deepcopy(t)
            print('List: ',exp)
            print('Tensor: ', torch.tensor(exp))
            episode_trajectory[episode_index:episode_index + len(exp)] = torch.tensor(exp)
            episode_index += len(exp)'''
            if done:
                exp = copy.deepcopy(zip(ep_observations[:idx],ep_actions[:idx],ep_rewards[:idx].tolist(),ep_logprobs[:idx,0],ep_next_observations[:idx],ep_dones[:idx]))
                queue.put(exp)
                env.reset()
                observation = env.get_observation()
                observations[id] = observation
                ep_observations.fill(0)
                ep_actions.fill(0)
                ep_rewards.fill(0)
                ep_logprobs.fill(0)
                ep_next_observations.fill(0)
                ep_dones.fill(0)
                idx = 0
                step_control[id] = 1
            else:
                observations[id] = torch.from_numpy(next_observation)
                observation = next_observation
                step_control[id] = 1

def launch_processes(envs, observations, step_control, stop_collecting,waitForLearner,queue, max_episode_length,logprobs = None,num_instances=1):

    process_list = []

    for i in range(num_instances):
        if logprobs is not None:
            p = mp.Process(target = process_target_with_log_probs, args=(envs[i],observations,step_control,stop_collecting,i,queue,logprobs, max_episode_length,) )
        else:
            p = mp.Process(target = process_target, args=(envs[i],observations,step_control,stop_collecting,waitForLearner,i,queue,max_episode_length,) )
        p.start()
        process_list.append(p)

    return process_list
