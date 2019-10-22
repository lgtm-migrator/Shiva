
from settings import shiva
from .Learner import Learner

class SingleAgentImitationLearner(Learner):
    def __init__(self,
                id,
                agents,
                environments,
                algorithm,
                data,
                configs):

        super().__init__(
                        id,
                        agents,
                        environments,
                        algorithm,
                        data,
                        configs,
                        )



        #I'm thinking about getting the saveFrequency here from the config and saving it in self
        self.saveFrequency = configs['Learner']['save_frequency']
        self.agents = [None] * self.configs['Learner']['dagger_iterations']


    def run(self):
        self.supervised_update()
        print('Supervised Learning is complete!')
        print('Loss:',self.supervised_alg.loss)
        self.imitation_update()

    '''def test_run(self,agent,episodes):
        for ep in range(episodes):
            self.env.reset()
            self.totalReward = 0

            done=False
            while not done:
                observation = self.env.get_observation()
                #action = agent.policy(torch.FloatTensor(observation))
                action = self.supervised_alg.onenp.argmax(agent.policy(torch.tensor(observation).float()).detach())
                expert_action = self.supervised_alg.get_action(self.expert_agent,observation)
                print('Imitation action: ',action,' Expert Action: ', expert_action)
                next_observation, reward, done = self.env.step(action)
                self.totalReward += 1

            print('Episode Reward:',self.totalReward)'''




    def supervised_update(self):

        for ep_count in range(self.configs['Learner']['supervised_episodes']):
            print(ep_count)

            self.env.reset()

            self.totalReward = 0

            done = False
            while not done:
                done = self.supervised_step(ep_count)
                shiva.add_summary_writer(self, self.agents[0], 'Loss', self.supervised_alg.get_loss(), self.env.get_current_step())

        # make an environment close function
        # self.env.close()
        self.env.env.close()

        #self.supervised_train()

    def imitation_update(self):

        for iter_count in range(1,self.configs['Learner']['dagger_iterations']):


            for ep_count in range(self.configs['Learner']['imitation_episodes']):
                print(ep_count)
                self.env.reset()

                self.totalReward = 0

                done = False
                while not done:
                    done = self.imitation_step(ep_count,iter_count)
                    shiva.add_summary_writer(self, self.agents[iter_count-1], 'Loss', self.imitation_alg.get_loss(), self.env.get_current_step())

                    self.env.env.close()


            #self.imitation_train(iter_count)
            print('Policy ',iter_count, ' complete!')
            print('Loss: ',self.imitation_alg.loss)


    # Function to step throught the environment
    def supervised_step(self,ep_count):
        #self.env.load_viewer()

        observation = self.env.get_observation()

        action = self.supervised_alg.get_action(self.expert_agent, observation)

        next_observation, reward, done = self.env.step(action)

        # Write to tensorboard
        shiva.add_summary_writer(self, self.expert_agent, 'Reward', reward, self.env.get_current_step())

        # Cumulate the reward
        self.totalReward += reward[0]

        self.replay_buffer.append([observation, action, reward, next_observation, done])
        self.supervised_alg.update(self.agents[0],self.replay_buffer.sample(), self.env.get_current_step())

        # when the episode ends
        if done:
            # add values to the tensorboard
            shiva.add_summary_writer(self, self.agents[0], 'Total Reward', self.totalReward, ep_count)
            shiva.add_summary_writer(self, self.agents[0], 'Average Loss per Episode', self.supervised_alg.get_average_loss(self.env.get_current_step()), ep_count)
            print(self.totalReward)



        # Save the model periodically
        if self.env.get_current_step() % self.saveFrequency == 0:
            pass

        return done

    def imitation_step(self,ep_count,iter_count):

        #if iter_count == 4:
            #self.env.load_viewer()

        observation = self.env.get_observation()

        action = self.imitation_alg.find_best_action(self.agents[iter_count-1].policy, observation)#, self.env.get_current_step())

        next_observation, reward, done, = self.env.step(action)

        shiva.add_summary_writer(self, self.agents[iter_count-1], 'Reward', reward, self.env.get_current_step())

        self.totalReward += reward[0]

        self.replay_buffer.append([observation,action,reward,next_observation,done])
        self.imitation_alg.update(self.agents[iter_count],self.expert_agent, self.replay_buffer.sample(), self.env.get_current_step())


        #print('Total Reward: ', self.totalReward)
        #print('Average Loss per Episode', self.supervised_alg.get_average_loss(self.env.get_current_step()))
        # when the episode ends
        if done:
            # add values to the tensorboard
            shiva.add_summary_writer(self, self.agents[iter_count], 'Total Reward', self.totalReward, ep_count)
            shiva.add_summary_writer(self, self.agents[iter_count], 'Average Loss per Episode', self.imitation_alg.get_average_loss(self.env.get_current_step()), ep_count)
            print(self.totalReward)


        return done


    def create_environment(self):
        # create the environment and get the action and observation spaces
        self.env = Environment.initialize_env(self.configs['Environment'])


    def get_agents(self):
        return self.agents

    def get_algorithm(self):
        return self.algorithm

    # Initialize the model
    def launch(self):



        # Launch the environment
        self.create_environment()

        # Launch the algorithm which will handle the
        self.supervised_alg,self.imitation_alg = Algorithm.initialize_algorithm(self.env.get_observation_space(), self.env.get_action_space(), [self.configs['Algorithm'], self.configs['Agent'], self.configs['Network']])
        #self.imitation_alg =  Algorithm.initialize_algorithm(self.env.get_observation_space(), self.env.get_action_space(), [self.configs['Algorithm'], self.configs['Agent'], self.configs['Network']])

        for i in range(len(self.agents)):
            self.agents[i] = self.supervised_alg.create_agent(self.id_generator())

        self.expert_agent = self.load_agent(self.configs['Learner']['expert_agent'])


        # Basic replay buffer at the moment
        self.replay_buffer = ReplayBuffer.initialize_buffer(self.configs['ReplayBuffer'], 1, self.env.get_action_space(), self.env.get_observation_space())
        #self.imitation_buffer = ReplayBuffer.initialize_buffer(self.configs['ReplayBuffer'], 1, self.env.get_action_space(), self.env.get_observation_space())


    # do this for travis
    def load_agent(self, path):#,configs

        return shiva._load_agents(path)[0]


    def makeDirectory(self, root):

        # make the learner folder name
        root = root + '/learner{}'.format(self.id)

        # make the folder
        subprocess.Popen("mkdir " + root, shell=True)

        # return root for reference
        return root