#!/bin/bash

clean_state () {
    # Remove old game server credentials
    echo "Cleaning previous master server state"
    su pwn3 -c "psql master -f $PWN3/setup/clean.sql"
}

stop_db () {
    # Stop db gracefully
    echo "Stopping database"
    su postgres -c "/etc/init.d/postgresql stop"
    sleep 5 
}

generate_credentials () {
    # Generate master server credentials for game servers to authenticate
    echo "Generating master server credentials"
    su pwn3 -c "cd $PWN3/server/MasterServer/ && ./MasterServer --create-server-account > $PWN3/server/creds"
    USER=$(cat $PWN3/server/creds | grep 'Username:' | awk -F ':' '{sub(" ", "", $2); print $2}')
    PASS=$(cat $PWN3/server/creds | grep 'Password:' | awk -F ':' '{sub(" ", "", $2); print $2}')
    cat >$PWN3/client/PwnAdventure3_Data/PwnAdventure3/PwnAdventure3/Content/Server/server.ini <<EOL
[MasterServer]
Hostname=master.pwn3
Port=3333

[GameServer]
Hostname=game.pwn3
Port=3000
Username=$USER
Password=$PASS
Instances=5
EOL
}

trap stop_db SIGTERM SIGKILL SIGINT SIGHUP

# Start the db server
su postgres -c "/etc/init.d/postgresql start"
su postgres -c "pg_isready"
while [[ $? -ne 0 ]]; do
    sleep 5
    su postgres -c "pg_isready"
done

# Clean up from previous state
clean_state

# Always generate new credentials
generate_credentials

# Run server
echo "Starting MasterServer"
su pwn3 -c "cd $PWN3/server/MasterServer/ && ./MasterServer" &
echo "MasterServer started"

child=$!
wait  "$child"

stop_db
