import neuralmmo_st as nmmo
import argparse
# from forge.trinity import smith, Trinity, Pantheon, God, Sword

def parseArgs():
    parser = argparse.ArgumentParser('Projekt Godsword')
    parser.add_argument('--nRealm', type=int, default='1', 
            help='Number of environments (1 per core)')
    parser.add_argument('--api', type=str, default='native', 
            help='API to use (native/vecenv)')
    parser.add_argument('--ray', type=str, default='default', 
            help='Ray mode (local/default/remote)')
    parser.add_argument('--render', action='store_true', default=False, 
            help='Render env')
    parser.add_argument('blueTeamSize', metavar='B', type=int, default='3', help='size of blue team')
    parser.add_argument('redTeamSize',  metavar='R', type=int, default='3', help='size of red team')
    
    return parser.parse_args()

#Example runner using the (slower) vecenv api
#The actual vecenv spec was not designed for
#multiagent, so this is a best-effort facsimile
class GymExample:
    def __init__(self, config, args):
        self.env = nmmo.smith.VecEnv(config, args, self.step)
        #The environment is persistent. Reset only to start it.
        self.envsObs = self.env.reset()

        #the ANN used internally by Trinity
        self.ann = nmmo.ANN(config)

    #Runs a single step of each environment
    #With slow comms at each step
    def step(self):
        actions = []
        for obs in self.envsObs: #Environment
            atns = []
            for ob in obs: #Agent
                ent, stim = ob
                action, arguments, atnArgs, val = self.ann(ent, stim)
                atns.append((ent.entID, action, arguments, float(val)))
            actions.append(atns)
        self.envsObs, rews, dones, infos = self.env.step(actions)

    def run(self):
        while True:
            self.step()

class NativeExample:
    def __init__(self, config, args):
        trinity = nmmo.Trinity(nmmo.Pantheon, nmmo.God, nmmo.Sword)
        self.env = nmmo.smith.Native(config, args, trinity)

    def run(self):
        while True:
            self.env.run()

if __name__ == '__main__':
    args = parseArgs()
    assert args.api in ('native', 'vecenv')
    exper = nmmo.Experiments()
    exper.makeExps()
    exper.makeExp('sample', nmmo.Chaos, 128, test=True)
    config = exper.exps['testchaos128']

    if args.api == 'native':
        example = NativeExample(config, args)
    elif args.api == 'vecenv':
        example = GymExample(config, args)

    #Rendering by necessity snags control flow
    #This will automatically set local mode with 1 core
    if args.render:
        example.env.render()
    
    print("This is running")
    example.run()