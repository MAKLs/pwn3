#include <dlfcn.h>
#include <set>
#include <map>
#include <functional>
#include <cstring>
#include <vector>
#include "pwn3.h"

// Globals to push to player after each tick
float JUMP_SPEED = 1000;
float WALK_SPEED = 10000;
bool IS_FROZEN = false;
Vector3 FROZEN_POSITION;


bool Player::CanJump() {
    // Always can jump
    return 1;
}


void Player::Chat(const char* message) {
    // Print message
    printf("[%s] -> \"%s\"\n", this->GetPlayerName(), message);
    
    // Teleport
    if (strncmp(message, "tp ", 3) == 0) {
        Vector3 new_position;
        sscanf(message + 3, "%f %f %f", &(new_position.x), &(new_position.y), &(new_position.z));
        this->SetPosition(new_position);
    }
    // Adjust z coordinates only
    else if (strncmp(message, "tz ", 3) == 0) {
        float new_z;
        Vector3 new_position = this->GetPosition();
        sscanf(message + 3, "%f", &new_z);
        new_position.z += new_z;
        this->SetPosition(new_position);
    }
    // Freeze position
    else if (strncmp(message, "!", 1) == 0) {
        IS_FROZEN = !IS_FROZEN;
        FROZEN_POSITION = this->GetPosition();
    }
    // Set jump speed
    else if (strncmp(message, "js ", 3) == 0) {
        sscanf(message + 3, "%f", &(JUMP_SPEED));
    }
    // Set walk speed
    else if (strncmp(message, "ws ", 3) == 0) {
        sscanf(message + 3, "%f", &(WALK_SPEED));
    }
    // Get position
    else if (strncmp(message, "gp", 2) == 0) {
        Vector3 position = this->GetPosition();
        printf("<Position> %f %f %f", position.x, position.y, position.z);
    }
}


void World::Tick(float f) {
    // Get the real GameWorld
    ClientWorld* world = *((ClientWorld**)(dlsym(RTLD_NEXT, "GameWorld")));

    // Get player
    IPlayer* iplayer = world->m_activePlayer.m_object;
    Player* player = ((Player*)(iplayer));

    // Increase speed
    player->m_walkingSpeed = WALK_SPEED;

    // Increase jump
    player->m_jumpSpeed = JUMP_SPEED;

    // Persist position if frozen
    if (IS_FROZEN) {
        // Counter gravity
        Vector3 pos = Vector3(FROZEN_POSITION.x, FROZEN_POSITION.y, FROZEN_POSITION.z);
        pos.z += 60;
        player->SetPosition(pos);
    }
}