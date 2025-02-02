#!/usr/bin/env python
# encoding: utf-8
import os, subprocess

class Team(object):
  """ Abstract class. Handles launching players from 3rd party binaries. """

  def __init__(self, name, binaryPath, libDir, options, offenseOrder,
               defenseOrder):
    """
    Creates a team.

    name: name of the team
    binaryPath: absolute path of the executable
    libDir: library dependencies directory
    options: team-specific parameters for executable in string format
    offenseOrder: order to prioritize offensive unums (do not include 0)
    defenseOrder: order to prioritize defensive unums (do not include 0)
    """
    self._name = name
    self._binary_path = binaryPath
    self._lib_dir = libDir
    self._options = options
    self._offense_order = offenseOrder
    self._defense_order = defenseOrder

  def launch_npc(self, player_num):
    """
    Abstract method that should be overrided by subclasses. Launches an
    npc with player number player_num.  The method that overrides this
    should call start_npc_process. See examples below.
    """
    pass

  def start_npc_proc(self, launchOpts=None):
    """
    Launches a player using the team-specific binary launchOpts
    should be used to append player specific options (e.g., helios
    uses '-g' to signify launching a goalie )

    Returns a Popen process object
    """
    player_cmd = self._binary_path
    player_cmd += ' %s' % (self._options)
    if launchOpts != None:
      player_cmd += ' %s' % (launchOpts)
    kwargs = {'stdout':open('/dev/null', 'w'),
              'stderr':open('/dev/null', 'w')}
    env = dict(os.environ)
    if self._lib_dir != None:
      env['LD_LIBRARY_PATH'] = self._lib_dir
    p = subprocess.Popen(player_cmd.split(' '), env=env, shell = False, **kwargs)
    return p


class Agent2d(Team):
  def __init__(self, name, baseDir, libDir, binaryName, logDir, record,
               host='localhost', port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '-t %s -p %i --config_dir %s/config/formations-dt --log_dir %s '\
              '--player-config %s/config/player.conf'\
              % (name, port, baseDir, logDir, baseDir)
    if record:
      options += ' --record'
    offenseOrder =  [1,2,3,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,2,3,4,5,6,7,8,9,10,11]
    super(Agent2d, self).__init__(name, binaryPath, libDir, options,
                                  offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)


class Helios(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-conf-dir %s/data/formations '\
              '--role-conf %s/data/role.conf --ball-table %s/data/ball_table.dat '\
              '--chain-search-method BestFirstSearch --evaluator-name Default '\
              '--max-chain-length 4 --max-evaluate-size 1000 '\
              '--sirm-evaluator-param-dir %s/data/sirm_evaluator/ '\
              '--goalie-position-dir %s/data/goalie_position/ '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opponent_data/ -p %d'\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir,
                 baseDir, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios18(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-dir %s/data/formations '\
              '--setplay-dir %s/data/setplay '\
              '--formation-conf %s/data/formation.conf '\
              '--hetero-conf %s/data/hetero.conf '\
              '--overwrite-formation-conf %s/data/overwrite_formation.conf '\
              '--ball-table %s/data/ball_table.dat '\
              '--intercept-evaluator-name default '\
              '--chain-search-method BestFirstSearch --evaluator-name Default '\
              '--max-chain-length 3 --max-evaluate-size 3000 '\
              '--svmrank-evaluator-model %s/data/svmrank_evaluator/model' \
              '--svmrank-intercept-evaluator-model %s/data/svmrank_intercept_evaluator/model' \
              '--neural-network-evaluator-dir %s/data/neural_network_evaluator/ ' \
              '--center-forward-free-move-model %s/data/center_forward_free_move/model '  \
              '--svm-formation-classifier-model %s/data/svm_formation_classifier/svm.model ' \
              '--goalie-position-dir %s/data/goalie_position/ '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opponent_data/ --record -p %d '\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir, baseDir, baseDir, baseDir,
                 baseDir, baseDir, baseDir, baseDir, baseDir, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios18, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)
  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios17(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-conf-dir %s/data/formations '\
              '--formation-conf %s/data/formation.conf '\
              '--overwrite-formation-conf %s/data/overwrite_formation.conf '\
              '--hetero-conf %s/data/hetero.conf '\
              '--ball-table %s/data/ball_table.dat '\
              '--chain-search-method BestFirstSearch '\
              '--evaluator-name Default '\
              '--max-chain-length 4 --max-evaluate-size 1000 '\
              '--sirm-evaluator-param-dir %s/data/sirm_evaluator/ '\
              '--svmrank-evaluator-model %s/data/svmrank_evaluator/model '\
              '--neural-network-evaluator-dir %s/data/neural_network_evaluator/ '\
              '--center-forward-free-move-model %s/data/center_forward_free_move/model '\
              '--svm-formation-classifier-model %s/data/svm_formation_classifier/svm.model '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opponent_data/ -p %d '\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir, baseDir, baseDir, 
                 baseDir, baseDir, baseDir, baseDir, baseDir, baseDir, port)

    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios17, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios16(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-conf-dir %s/data/formations '\
              '--formation-conf %s/data/formation.conf '\
              '--overwrite-formation-conf %s/data/overwrite_formation.conf '\
              '--hetero-conf %s/data/hetero.conf '\
              '--ball-table %s/data/ball_table.dat '\
              '--chain-search-method BestFirstSearch --evaluator-name Default '\
              '--max-chain-length 4 --max-evaluate-size 1000 '\
              '--sirm-evaluator-param-dir %s/data/sirm_evaluator/ '\
              '--svmrank-evaluator-model %s/data/svmrank_evaluator/model '\
              '--center-forward-free-move-model %s/data/center_forward_free_move/model '\
              '--goalie-position-dir %s/data/goalie_position/ '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opponent_data/ -p %d'\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir, baseDir,
                 baseDir, baseDir, baseDir, baseDir, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,2,3,4,5,6,7,9,10]
    defenseOrder =  [1,8,11,2,3,4,5,6,7,9,10]
    super(Helios16, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios15(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-conf-dir %s/data/formations '\
              '--formation-conf %s/data/formation.conf '\
              '--overwrite-formation-conf %s/data/overwrite_formation.conf '\
              '--hetero-conf %s/data/hetero.conf '\
              '--ball-table %s/data/ball_table.dat '\
              '--chain-search-method BestFirstSearch --evaluator-name Default '\
              '--max-chain-length 4 --max-evaluate-size 1000 '\
              '--sirm-evaluator-param-dir %s/data/sirm_evaluator/ '\
              '--svmrank-evaluator-model %s/data/svmrank_evaluator/model '\
              '--center-forward-free-move-model %s/data/center_forward_free_move/model '\
              '--goalie-position-dir %s/data/goalie_position/ '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opponent_data/ -p %d '\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir, baseDir, baseDir, 
                 baseDir, baseDir, baseDir, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios15, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)
    
class Helios14(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-conf-dir %s/data/formations '\
              '--formation-conf %s/data/formation.conf '\
              '--hetero-conf %s/data/hetero.conf '\
              '--overwrite-formation-conf %s/data/overwrite_formation.conf '\
              '--ball-table %s/data/ball_table.dat '\
              '--chain-search-method BestFirstSearch --evaluator-name Default '\
              '--max-chain-length 4 --max-evaluate-size 1000 '\
              '--sirm-evaluator-param-dir %s/data/sirm_evaluator/ '\
              '--goalie-position-dir %s/data/goalie_position/ '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opponent_data/ -p %d'\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir, baseDir, baseDir,
                 baseDir, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios14, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios12(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-conf-dir %s/data/formations '\
              '--role-conf %s/data/role.conf --ball-table %s/data/ball_table.dat '\
              '--chain-search-method BestFirstSearch --evaluator-name Default '\
              '--max-chain-length 4 --max-evaluate-size 1000 '\
              '--sirm-evaluator-param-dir %s/data/sirm_evaluator/ '\
              '--goalie-position-dir %s/data/goalie_position/ '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opponent_data/ -p %d'\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir,
                 baseDir, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios12, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios11(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--formation-conf-dir %s/data/formations '\
              '--role-conf %s/data/role.conf --ball-table %s/data/ball_table.dat '\
              '--evaluator-param-file %s/data/params '\
              '--max-chain-length 4 --max-evaluate-size 500 '\
              '--goalie-optimal-conf-dir %s/data/goalie_optimal_position/ '\
              '--intercept-conf-dir %s/data/intercept_probability/ '\
              '--opponent-data-dir %s/data/opp_data/ -p %d'\
              % (baseDir, host, name, baseDir, baseDir, baseDir, baseDir,
                 baseDir, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios11, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios10(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--config_dir %s/formations-4231 '\
              '--param-file %s/parameters/params -p %d'\
              % (baseDir, host, name, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios10, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios09(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--config_dir %s/formations-442 '\
              '-p %d'\
              % (baseDir, host, name, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios09, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios08(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--config_dir %s/formations-4231 '\
              '--param-file %s/parameters/params -p %d'\
              % (baseDir, host, name, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios08, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Helios07(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = '--player-config %s/player.conf -h %s -t %s '\
              '--config_dir %s/formations-4231 '\
              '--param-file %s/parameters/params -p %d'\
              % (baseDir, host, name, baseDir, baseDir, port)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Helios07, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)

class Cyrus(Team):
  def __init__(self, name, baseDir, libDir, binaryName, host='localhost',
               port=6000):
    binaryPath = os.path.join(baseDir, binaryName)
    options = ' -h %s -t %s -p %i --config_dir %s/formations-dt '\
              '--player-config %s/player.conf'\
              % (host, name, port, baseDir, baseDir)
    offenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    defenseOrder =  [1,8,11,4,5,6,7,8,9,10,11]
    super(Cyrus, self).__init__(name, binaryPath, libDir, options,
                                 offenseOrder, defenseOrder)

  def launch_npc(self, player_num):
    launchOpts = None
    if player_num == 1:
      launchOpts = '-g'
    print('Launch npc %s-%d' % (self._name, player_num))
    return self.start_npc_proc(launchOpts)