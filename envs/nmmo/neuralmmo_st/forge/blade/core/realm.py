import ray
import pickle
import numpy as np
from pdb import set_trace as T
import numpy as np

from forge import trinity as Trinity
from forge.blade import entity, core
from itertools import chain
from copy import deepcopy

class ActionArgs:
   def __init__(self, action, args):
      self.action = action
      self.args = args

class Realm:
   reachedMax = False

   def __init__(self, config, args, idx):
      #Random samples
      if config.SAMPLE:
         config = deepcopy(config)
         nent = np.random.randint(0, config.NENT)
         config.NENT = config.NPOP * (1 + nent // config.NPOP)
         print("[RealmInit]!!!! SAMPLE !!!! config.NENT = " + str(config.NENT) + "; config.NPOP=" + str(config.NPOP))
      self.world, self.desciples = core.Env(config, idx), {}
      self.config, self.args, self.tick = config, args, 0
      self.npop = config.NPOP
      print("[RealmInit] config.NENT = " + str(config.NENT) + "; config.NPOP=" + str(config.NPOP))

      self.env = self.world.env
      self.values = None

   def clientData(self):
      if self.values is None and hasattr(self, 'sword'):
         self.values = self.sword.anns[0].visVals()

      ret = {
            'environment': self.world.env,
            'entities': dict((k, v.packet()) for k, v in self.desciples.items()),
            'values': self.values
            }
      return pickle.dumps(ret)

   # Called before God.spawn()
   def spawn(self, isBlue, totalEntCount):
      if len(self.desciples) >= totalEntCount or Realm.reachedMax: #3 x 3 
         Realm.reachedMax = True # prevents respawn
         return

   # if len(self.desciples) >= self.config.NENT:
         # return

      entID, color = self.god.spawn(isBlue)
      ent = entity.Player(entID, color, self.config)
      self.desciples[ent.entID] = ent

      r, c = ent.pos
      self.world.env.tiles[r, c].addEnt(entID, ent)
      self.world.env.tiles[r, c].counts[ent.colorInd] += 1

   def cullDead(self, dead):
      for entID in dead:
         ent = self.desciples[entID]
         r, c = ent.pos
         self.world.env.tiles[r, c].delEnt(entID)
         self.god.cull(ent.annID)
         del self.desciples[entID]

   def stepWorld(self):
      ents = list(chain(self.desciples.values()))
      self.world.step(ents, [])

   def stepEnv(self):
      self.world.env.step()
      self.env = self.world.env.np()

   def stepEnt(self, ent, action, arguments):
      move, attack         = action
      moveArgs, attackArgs = arguments

      ent.move   = ActionArgs(move, moveArgs)
      ent.attack = ActionArgs(attack, attackArgs[0])
      print("[Realm-stepEnt]attackArgs=" + str(attackArgs))

   def getStim(self, ent):
      return self.world.env.stim(ent.pos, self.config.STIM)
      
   def getTick(self):
      return self.tick
   
   def incrementTick(self):
      self.tick += 1

@ray.remote # Active 
class NativeRealm(Realm):
   counter = 0
   counterLimit = 3
   def __init__(self, trinity, config, args, idx):
      super().__init__(config, args, idx)
      self.god = trinity.god(config, args)
      self.sword = trinity.sword(config, args)
      self.sword.anns[0].world = self.world
      
      print("[REALM]args=" + str(args))
      
      # for i in range(0,6):
         # self.spawn()
      bSize = np.clip(args.blueTeamSize, 0, 3)
      rSize = np.clip(args.redTeamSize, 0, 3)
      totalEntCount = bSize + rSize
      for i in range(0, bSize):
         self.spawn(True, totalEntCount)
      for i in range(0, rSize):
         self.spawn(False, totalEntCount)
      
 
   def stepEnts(self):
      # if ('counter' not in globals()):
         # global counter
         # counter = 0
      # counterLimit = 3
      
      dead = []
      print('NativeRealm-stepEnts. size=' + str(len(self.desciples.values())))
      for ent in self.desciples.values():
         if (int(ent.entID) < 0): ## Replace this with some other way to determine a controlled entity
             ent.step(self.world)
    
             if self.postmortem(ent, dead):
                continue
    
             stim = self.getStim(ent)
             action, arguments, val = self.sword.decide(ent, stim)
             ent.act(self.world, action, arguments, val)
    
             self.stepEnt(ent, action, arguments)
         else:
             ent.step(self.world)
    
             if self.postmortem(ent, dead):
                continue
    
             stim = self.getStim(ent)
             
             ### Pick an enemy ###
             
             # ### HUMAN INPUT   ###
             # enemy_entID = str(ent.entID)
             # if (counter > counterLimit):
               # inputString = input("Enemy ID (use self for no attack): ")
               # try:
                  # enemy_entID = str(inputString)
               # except:
                  # print(inputString + " not parsable to int. Using self")
                  # enemy_entID = str(ent.entID)
             # try:
               # enemy_ent = self.desciples[enemy_entID]
             # except:
               # print(str(enemy_entID) + " not found. Using self!")
               # #for ent in self.desciples.values():
               # #   print "desciple entID: " + str(ent.entID)
               # enemy_ent = ent
             # counter += 1
             # ### END HUMAN INPUT    ###
             
             ### PROCEDURAL INPUT ###
             enemy_ent = ent # placeholder until enemy finding routine created
             allEnts = self.desciples.values()
             ### END PROCEDURAL INPUT ###
             
             ### Done picking enemy ###
             
             action, arguments = self.sword.decide_CONTROLLED(ent, enemy_ent, stim, self.world, self.getTick(), allEnts)
             #print("[Realm]return action,arguments\n\n" + str(action) + "\n\n" + str(arguments))
             ent.act(self.world, action, arguments)
             #print("[Realm]ent.act")
    
             self.stepEnt(ent, action, arguments)             
             #print("[Realm]stepEnt")

      self.cullDead(dead)
      self.incrementTick()

   def postmortem(self, ent, dead):
      entID = ent.entID
      if not ent.alive or ent.kill:
         dead.append(entID)
         if not self.config.TEST:
            self.sword.collectRollout(entID, ent)
         return True
      return False

   def step(self):
      #self.spawn() # move to Init
      self.stepEnv()
      self.stepEnts()
      self.stepWorld()

   def run(self, swordUpdate=None):
      self.recvSwordUpdate(swordUpdate)

      updates = None
      while updates is None:
         self.step()
         updates, logs = self.sword.sendUpdate()
      return updates, logs

   def recvSwordUpdate(self, update):
      if update is None:
         return
      self.sword.recvUpdate(update)

   def recvGodUpdate(self, update):
      self.god.recv(update)

@ray.remote
class VecEnvRealm(Realm):
   #Use the default God behind the scenes for spawning
   def __init__(self, config, args, idx):
      super().__init__(config, args, idx)
      self.god = Trinity.God(config, args)

   def stepEnts(self, decisions):
      dead = []
      for tup in decisions:
         entID, action, arguments, val = tup
         ent = self.desciples[entID]
         ent.step(self.world)

         if self.postmortem(ent, dead):
            continue

         ent.act(self.world, action, arguments, val)
         self.stepEnt(ent, action, arguments)
      self.cullDead(dead)

   def postmortem(self, ent, dead):
      entID = ent.entID
      if not ent.alive or ent.kill:
         dead.append(entID)
         return True
      return False

   def step(self, decisions):
      decisions = pickle.loads(decisions)
      self.stepEnts(decisions)
      self.stepWorld()
      self.spawn()
      self.stepEnv()

      stims, rews, dones = [], [], []
      for entID, ent in self.desciples.items():
         stim = self.getStim(ent)
         stims.append((ent, self.getStim(ent)))
         rews.append(1)
      return pickle.dumps((stims, rews, None, None))

   def reset(self):
      self.spawn()
      self.stepEnv()
      return [(e, self.getStim(e)) for e in self.desciples.values()]


