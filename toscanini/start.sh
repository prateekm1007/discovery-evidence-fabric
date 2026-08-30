#!/bin/bash
# Toscanini service launcher — fully detached (setsid) so it survives
# the calling shell session, mirroring the gateway's start_new_session.
cd /home/z/my-project/discovery-evidence-fabric || exit 1
mkdir -p ENGINE_RUNS
setsid python3 -m toscanini.server >> ENGINE_RUNS/toscanini_server.log 2>&1 < /dev/null &
echo "toscanini service launched (pid $!)"
