from shiva.core.admin import Admin
from shiva.helpers.config_handler import load_class

class Learner(object):
    
    def __init__(self, learner_id, config):
        {setattr(self, k, v) for k,v in config['Learner'].items()}
        self.configs = config
        self.id = learner_id
        self.agentCount = 0
        self.ep_count = 0
        self.step_count = 0
        self.checkpoints_made = 0
        self.totalReward = 0

    def __getstate__(self):
        d = dict(self.__dict__)
        try:
            del d['env']
        except KeyError:
            del d['envs']
        return d
        try:
            del d['eval']
        except KeyError:
            pass
        try:
            # Imitation Learner for RoboCup
            del d['bot_process']
            del d['super_buffer']
            del d['comm']
        except KeyError:
            pass
        return d

    def collect_metrics(self, episodic=False):
        '''
            This works for Single Agent Learner
            For Multi Agent Learner we need to implemenet the else statement
        '''
        if hasattr(self, 'agent') and type(self.agent) is not list:
            metrics = self.alg.get_metrics(episodic) + self.env.get_metrics(episodic)
            count = self.env.done_count if episodic else self.env.step_count
            for metric_name, y_val in metrics:
                Admin.add_summary_writer(self, self.agent, metric_name, y_val, count)
        else:
            assert False, "The Learner attribute 'agent' was not found. Either name the attribute 'agent' or could be that MultiAgent Metrics are not yet supported."

    def checkpoint(self):
        assert hasattr(self, 'save_checkpoint_episodes'), "Learner needs 'save_checkpoint_episodes' attribute in config - put 0 if don't want to save checkpoints"
        if self.save_checkpoint_episodes > 0:
            t = self.save_checkpoint_episodes * self.checkpoints_made
            if self.env.done_count > t:
                print("%% Saving checkpoint at episode {} %%".format(self.env.done_count))
                Admin.update_agents_profile(self)
                self.checkpoints_made += 1

    def update(self):
        assert 'Not implemented'
        pass

    def step(self):
        assert 'Not implemented'
        pass

    def create_environment(self):
        env_class = load_class('shiva.envs', self.configs['Environment']['type'])
        return env_class(self.configs['Environment'])

    def get_agents(self):
        assert 'Not implemented'
        pass

    def get_algorithm(self):
        assert 'Not implemented'
        pass

    def launch(self):
        assert 'Not implemented'
        pass

    def save(self):
        Admin.save(self)

    def load(self, attrs):
        for key in attrs:
            setattr(self, key, attrs[key])
    
    def close(self):
        pass

    def get_id(self):
        id = self.agentCount
        self.agentCount +=1
        return id