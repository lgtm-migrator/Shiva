# Project Title

Deep reinforcement/imitation learning pipeline leveraging population based training for continuous and discrete action spaces. Adaptable to game environments by creating a game specific environment wrapper.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.


### Installing

Create directory to hold repos.

```
mkdir shiva
cd shiva
```


Get the RCSSSERVER Repo:

```
git clone https://github.com/nflux/rcssserver.git
cd rcssserver
cd ..
```

Get the LIBRCSC Repo:

```
git clone https://github.com/nflux/librcsc.git
cd librcsc
cd ..
```

Get the Control-Tasks Repo:

```
git clone https://github.com/nflux/Control-Tasks.git
cd Control-Tasks
```
```
cd envs/rc_soccer/HFO
bash recompile_start.sh
```


###Training instructions:

from shiva/Control-Tasks run

```
python main.py
```

--env options: {rc,nmmo}

--conf options {rc_cpu,rc_gpu,rc_multi_gpu}
