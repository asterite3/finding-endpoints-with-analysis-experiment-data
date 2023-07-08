#!/bin/bash -ex

sudo ip link add teststands type dummy && \
    sudo ip addr add 100.72.55.11/32 dev teststands || \
    echo "Adding interface and addr failed, probably it already existed"
