from settings import shiva

class Learner(object):
    
    def __init__(self,
                id: "An id generated by metalearner to index the learner.",
                agents : list,
                environments : list,
                algorithm : str,
                data : list,
                configs: dict
                ):
        self.id = id
        self.agents = agents
        self.environments = environments
        self.algorithm = algorithm
        self.data = None
        self.agentCount = 0
        self.configs = configs

    def update(self):
        pass

    def step(self):
        pass

    def create_env(self, alg):
        pass

    def get_agents(self):
        pass

    def get_algorithm(self):
        pass

    def launch(self):
        pass

    def save(self):
        shiva.save(self)

    def load(self, attrs):
        for key in attrs:
            setattr(self, key, attrs[key])

    def id_generator(self):
        id = self.agentCount
        self.agentCount +=1
        return id