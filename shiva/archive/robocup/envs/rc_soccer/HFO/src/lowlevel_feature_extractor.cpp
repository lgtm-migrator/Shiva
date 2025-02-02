#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include "lowlevel_feature_extractor.h"
#include <rcsc/common/server_param.h>

using namespace rcsc;

LowLevelFeatureExtractor::LowLevelFeatureExtractor(int num_teammates,
                                                   int num_opponents,
                                                   bool playing_offense) :
    FeatureExtractor(num_teammates, num_opponents, playing_offense)
{
  assert(numTeammates >= 0);
  assert(numOpponents >= 0);
  numFeatures = num_basic_features +
      features_per_player * (numTeammates + numOpponents);
  numFeatures += numTeammates + numOpponents; // largest open angle to goal
  numFeatures += numTeammates; // largest open angle to player (pass)
  numFeatures += numTeammates + numOpponents; // Uniform numbers
  numFeatures += 2; // Self x,y
  numFeatures += 2 * (numTeammates + numOpponents); // Teammates, Opponents x,y
  numFeatures += 2; // Ball x, y
  numFeatures++; // action state
  numFeatures += 2; // Possesor indicators
  numFeatures++; // timestep
  feature_vec.resize(numFeatures);
}

LowLevelFeatureExtractor::~LowLevelFeatureExtractor() {}

const std::vector<float>&
LowLevelFeatureExtractor::ExtractFeatures(const rcsc::WorldModel& wm,
					  bool last_action_status, hfo::Player player_on_ball, long ep_end_time) {
  featIndx = 0;
  const ServerParam& SP = ServerParam::i();
  // ======================== SELF FEATURES ======================== //
  const SelfObject& self = wm.self();
  const Vector2D& self_pos = self.pos();
  const AngleDeg& self_ang = self.body();
  const PlayerPtrCont& teammates = wm.teammatesFromSelf();
  const PlayerPtrCont& opponents = wm.opponentsFromSelf();
  // const AbstractPlayerCont& allPlayers = wm.allPlayers();
  // const AbstractPlayerCont& theirPlayers = wm.theirPlayers();

  // std::ofstream myfile;
  // myfile.open("example.txt", std::ios_base::app);
  // for(AbstractPlayerCont::const_iterator it=allPlayers.begin(); it != allPlayers.end(); it++){
  //   const AbstractPlayerObject* po = *it;
  //   myfile << "Player: " << po->side() << " " << po->pos().x << " " << po->pos().y << std::endl;
  // }

  // std::ofstream myfile2;
  // myfile2.open("example2.txt", std::ios_base::app);
  // for(AbstractPlayerCont::const_iterator it=theirPlayers.begin(); it != theirPlayers.end(); it++){
  //   const AbstractPlayerObject* po = *it;
  //   myfile2 << "Player: " << po->side() << " " << po->pos().x << " " << po->pos().y << std::endl;
  // }

  addFeature(self.posValid() ? FEAT_MAX : FEAT_MIN);
  // ADD_FEATURE(self_pos.x);
  // ADD_FEATURE(self_pos.y);

  // Direction and speed of the agent.
  // addFeature(self.velValid() ? FEAT_MAX : FEAT_MIN);
  if (self.velValid()) {
    addAngFeature(self_ang - self.vel().th());
    addNormFeature(self.speed(), 0., observedSelfSpeedMax);
  } else {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }

  // Global Body Angle -- 0:right -90:up 90:down 180/-180:left
  addAngFeature(self_ang);

  // Neck Angle -- We probably don't need this unless we are
  // controlling the neck manually.
  // std::cout << "Face Error: " << self.faceError() << std::endl;
  // if (self.faceValid()) {
  //   std::cout << "FaceAngle: " << self.face() << std::endl;
  // }

  addNormFeature(self.stamina(), 0., observedStaminaMax);
  addFeature(self.isFrozen() ? FEAT_MAX : FEAT_MIN);

  // Probabilities - Do we want these???
  // std::cout << "catchProb: " << self.catchProbability() << std::endl;
  // std::cout << "tackleProb: " << self.tackleProbability() << std::endl;
  // std::cout << "fouldProb: " << self.foulProbability() << std::endl;

  // Features indicating if we are colliding with an object
  addFeature(self.collidesWithBall()   ? FEAT_MAX : FEAT_MIN);
  addFeature(self.collidesWithPlayer() ? FEAT_MAX : FEAT_MIN);
  addFeature(self.collidesWithPost()   ? FEAT_MAX : FEAT_MIN);
  addFeature(self.isKickable()         ? FEAT_MAX : FEAT_MIN);

  // inertiaPoint estimates the ball point after a number of steps
  // self.inertiaPoint(n_steps);

  // ======================== LANDMARK FEATURES ======================== //
  // Top Bottom Center of Goal
  rcsc::Vector2D goalCenter(pitchHalfLength, 0.);
  addLandmarkFeatures(goalCenter, self_pos, self_ang);
  rcsc::Vector2D goalPostTop(pitchHalfLength, -goalHalfWidth);
  addLandmarkFeatures(goalPostTop, self_pos, self_ang);
  rcsc::Vector2D goalPostBot(pitchHalfLength, goalHalfWidth);
  addLandmarkFeatures(goalPostBot, self_pos, self_ang);

  // Top Bottom Center of Penalty Box
  rcsc::Vector2D penaltyBoxCenter(pitchHalfLength - penaltyAreaLength, 0.);
  addLandmarkFeatures(penaltyBoxCenter, self_pos, self_ang);
  rcsc::Vector2D penaltyBoxTop(pitchHalfLength - penaltyAreaLength,
                               -penaltyAreaWidth / 2.);
  addLandmarkFeatures(penaltyBoxTop, self_pos, self_ang);
  rcsc::Vector2D penaltyBoxBot(pitchHalfLength - penaltyAreaLength,
                               penaltyAreaWidth / 2.);
  addLandmarkFeatures(penaltyBoxBot, self_pos, self_ang);

  // Corners of the Playable Area
  rcsc::Vector2D centerField(0., 0.);
  addLandmarkFeatures(centerField, self_pos, self_ang);

  //The code below is the original HFO, it was replaced by full field
  //rcsc::Vector2D cornerTopLeft(0, -pitchHalfWidth);
  rcsc::Vector2D cornerTopLeft(-pitchHalfLength, -pitchHalfWidth);
  addLandmarkFeatures(cornerTopLeft, self_pos, self_ang);

  rcsc::Vector2D cornerTopRight(pitchHalfLength, -pitchHalfWidth);
  addLandmarkFeatures(cornerTopRight, self_pos, self_ang);

  rcsc::Vector2D cornerBotRight(pitchHalfLength, pitchHalfWidth);
  addLandmarkFeatures(cornerBotRight, self_pos, self_ang);

  //The code below is the original HFO, it was replaced by full field
  //rcsc::Vector2D cornerBotLeft(0, pitchHalfWidth);
  rcsc::Vector2D cornerBotLeft(-pitchHalfLength, pitchHalfWidth);
  addLandmarkFeatures(cornerBotLeft, self_pos, self_ang);

  // Distances to the edges of the playable area
  if (self.posValid()) {
    // Based off left sides view the right side is reversed
    //addDistFeature(self_pos.x, pitchHalfLength);
    addDistFeature(pitchHalfLength + self_pos.x, pitchLength);
    // Distance to Right field line
    //addDistFeature(pitchHalfLength - self_pos.x, pitchHalfLength);
    addDistFeature(pitchHalfLength - self_pos.x, pitchLength);
    // Distance to top field line
    addDistFeature(pitchHalfWidth + self_pos.y, pitchWidth);
    // Distance to Bottom field line
    addDistFeature(pitchHalfWidth - self_pos.y, pitchWidth);
  } else {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }

  // ======================== BALL FEATURES ======================== //
  const BallObject& ball = wm.ball();
  // Angle and distance to the ball
  // addFeature(ball.rposValid() ? FEAT_MAX : FEAT_MIN);
  if (ball.rposValid()) {
    addLandmarkFeatures(ball.pos(), self_pos, self_ang);
    // addAngFeature(ball.angleFromSelf());
    // addDistFeature(ball.distFromSelf(), maxHFORadius);
  } else {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }
  // Velocity and direction of the ball
  // addFeature(ball.velValid() ? FEAT_MAX : FEAT_MIN);
  if (ball.velValid()) {
    // SeverParam lists ballSpeedMax a 2.7 which is too low
    addNormFeature(ball.vel().r(), 0., observedBallSpeedMax);
    addAngFeature(ball.vel().th());
  } else {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }

  // largest open goal angle of self
  addNormFeature(calcLargestGoalAngleTeam(wm, self_pos), 0., M_PI);

  assert(featIndx == num_basic_features);

  // teammate's open angle to goal
  int detected_teammates = 0;
  for (PlayerPtrCont::const_iterator it=teammates.begin(); it != teammates.end(); ++it) {
    const PlayerObject* teammate = *it;
    if (valid(teammate) && teammate->unum() > 0 && detected_teammates < numTeammates) {
      addNormFeature(calcLargestGoalAngleTeam(wm, teammate->pos()), 0., M_PI);
      detected_teammates++;
    }
  }
  // Add -2 features for any missing teammates
  for (int i=detected_teammates; i<numTeammates; ++i) {
    addFeature(FEAT_INVALID);
  }

  // opponent's open angle to goal
  int detected_opponents = 0;
  for (PlayerPtrCont::const_iterator it=opponents.begin(); it != opponents.end(); ++it) {
    const PlayerObject* opponent = *it;
    if (valid(opponent) && opponent->unum() > 0 && detected_opponents < numOpponents) {
      addNormFeature(calcLargestGoalAngleOpp(wm, -opponent->pos()), 0., M_PI);
      detected_opponents++;
    }
  }
  // Add -2 features for any missing teammates
  for (int i=detected_opponents; i<numOpponents; ++i) {
    addFeature(FEAT_INVALID);
  }

  // open angle to teammates, slices up the opponents in terms of the teammates
  detected_teammates = 0;
  for (PlayerPtrCont::const_iterator it=teammates.begin(); it != teammates.end(); ++it) {
    const PlayerObject* teammate = *it;
    if (valid(teammate) && teammate->unum() > 0 && detected_teammates < numTeammates) {
      addNormFeature(calcLargestTeammateAngle(wm, self_pos, teammate->pos()),0.,M_PI);
      detected_teammates++;
    }
  }
  // Add -2 features for any missing teammates
  for (int i=detected_teammates; i<numTeammates; ++i) {
    addFeature(FEAT_INVALID);
  }

  // // open angle to opponents, slices up the teammates in terms of the opponents
  // detected_opponents = 0;
  // for (PlayerPtrCont::const_iterator it=opponents.begin(); it != opponents.end(); ++it) {
  //   const PlayerObject* opponent = *it;
  //   if (valid(opponent) && opponent->unum() > 0 && detected_opponents < numOpponents) {
  //     addNormFeature(calcLargestOpenOpponentAngle(wm, self_pos, opponent->pos()),0,M_PI);
  //     detected_opponents++;
  //   }
  // }
  // // Add zero features for any missing opponents
  // for (int i=detected_opponents; i<numOpponents; ++i) {
  //   addFeature(0);
  // }

  // ======================== TEAMMATE FEATURES ======================== //
  // Vector of PlayerObject pointers sorted by increasing distance from self
  detected_teammates = 0;
  // const PlayerPtrCont& teammates = wm.teammatesFromSelf();
  for (PlayerPtrCont::const_iterator it = teammates.begin();
       it != teammates.end(); ++it) {
    PlayerObject* teammate = *it;
    if (teammate->unum() > 0 &&
        detected_teammates < numTeammates) {
      addPlayerFeatures(*teammate, self_pos, self_ang);
      detected_teammates++;
    }
  }
  // Add -2 features for any missing teammates
  for (int i=detected_teammates; i<numTeammates; ++i) {
    for (int j=0; j<features_per_player; ++j) {
      addFeature(FEAT_INVALID);
    }
  }

  // ======================== OPPONENT FEATURES ======================== //
  detected_opponents = 0;
  // const PlayerPtrCont& opponents = wm.opponentsFromSelf();
  for (PlayerPtrCont::const_iterator it = opponents.begin();
       it != opponents.end(); ++it) {
    PlayerObject* opponent = *it;
    if (opponent->unum() > 0 &&
        detected_opponents < numOpponents) {
      addPlayerFeatures(*opponent, self_pos, self_ang);
      detected_opponents++;
    }
  }
  // Add -2 features for any missing opponents
  for (int i=detected_opponents; i<numOpponents; ++i) {
    for (int j=0; j<features_per_player; ++j) {
      addFeature(FEAT_INVALID);
    }
  }

  // ========================= UNIFORM NUMBERS ========================== //
  detected_teammates = 0;
  for (PlayerPtrCont::const_iterator it = teammates.begin();
       it != teammates.end(); ++it) {
    PlayerObject* teammate = *it;
    if (teammate->unum() > 0 &&
        detected_teammates < numTeammates) {
      int unum = teammate->unum();
      if(unum == 8) {
        unum = 2;
      } else if(unum == 11) {
        unum = 3;
      }
      addFeature(unum/100.0);
      detected_teammates++;
    }
  }
  // Add -1 features for any missing teammates
  for (int i=detected_teammates; i<numTeammates; ++i) {
    addFeature(FEAT_MIN);
  }

  detected_opponents = 0;
  for (PlayerPtrCont::const_iterator it = opponents.begin();
       it != opponents.end(); ++it) {
    PlayerObject* opponent = *it;
    if (opponent->unum() > 0 &&
        detected_opponents < numOpponents) {
      int unum = opponent->unum();
      if(unum == 8) {
        unum = 2;
      } else if(unum == 11) {
        unum = 3;
      }
      addFeature(unum/100.0);
      detected_opponents++;
    }
  }
  // Add -1 features for any missing opponents
  for (int i=detected_opponents; i<numOpponents; ++i) {
    addFeature(FEAT_MIN);
  }

  // Self x-position & y-position
  if(self.posValid()) {
    addNormFeature(self_pos.x, -SP.pitchHalfLength(), SP.pitchHalfLength());
    addNormFeature(self_pos.y, -SP.pitchHalfWidth(), SP.pitchHalfWidth());
  } else {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }
  

  // Teammates x-pos & y-pos
  detected_teammates = 0;
  for(PlayerPtrCont::const_iterator it=teammates.begin(); it != teammates.end(); ++it) {
    const PlayerObject* teammate = *it;
    if(valid(teammate) && detected_teammates < numTeammates) {
      addNormFeature(teammate->pos().x, -SP.pitchHalfLength(), SP.pitchHalfLength());
      addNormFeature(teammate->pos().y, -SP.pitchHalfWidth(), SP.pitchHalfWidth());
      detected_teammates++;
    }
  }

  // Add -2 features for any missing teammates
  for (int i=detected_teammates; i<numTeammates; ++i) {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }

  // Opponents x-pos & y-pos
  detected_opponents = 0;
  for(PlayerPtrCont::const_iterator it=opponents.begin(); it != opponents.end(); ++it) {
    const PlayerObject* opponent = *it;
    if(valid(opponent) && detected_opponents < numOpponents) {
      addNormFeature(opponent->pos().x, -SP.pitchHalfLength(), SP.pitchHalfLength());
      addNormFeature(opponent->pos().y, -SP.pitchHalfWidth(), SP.pitchHalfWidth());
      detected_opponents++;
    }
  }

  // Add -2 features for any missing opponents
  for (int i=detected_opponents; i<numOpponents; ++i) {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }

  // Ball x-pos & Ball y-pos
  if(wm.ball().rposValid()) {
    addNormFeature(wm.ball().pos().x, -SP.pitchHalfLength(), SP.pitchHalfLength());
    addNormFeature(wm.ball().pos().y, -SP.pitchHalfWidth(), SP.pitchHalfWidth());
  } else {
    addFeature(FEAT_INVALID);
    addFeature(FEAT_INVALID);
  }
  
  if (last_action_status) {
    addFeature(FEAT_MAX);
  } else {
    addFeature(FEAT_MIN);
  }

  // std::ofstream outfile;
  // outfile.open("test.txt", std::ios_base::app);
  // outfile << "This is the side " << player_on_ball.side << " This is the unum " << player_on_ball.unum << std::endl;
  int unum = player_on_ball.unum;
  if(unum == 8) {
    unum = 2;
  } else if(unum == 11) {
    unum = 3;
  }
  if(player_on_ball.side == hfo::LEFT) {
    addFeature(unum/100.0);
    addFeature(0);
  } else if(player_on_ball.side == hfo::RIGHT) {
    addFeature(0);
    addFeature(unum/100.0);
  } else {
    addFeature(0);
    addFeature(0);
  }
  
  addFeature((wm.fullstateTime().cycle() - ep_end_time)/1000.0);

  assert(featIndx == numFeatures);
  checkFeatures();
  return feature_vec;
}

bool LowLevelFeatureExtractor::valid(const rcsc::PlayerObject* player) {
  if (!player) {return false;} //avoid segfaults
  const rcsc::Vector2D& pos = player->pos();
  if (!player->posValid()) {
    return false;
  }
  return pos.isValid();
}