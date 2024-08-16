#!/bin/bash

# IPs and configuration
MIKROTIK_IP="192.168.88.1"
TENDA_IP="192.168.0.1"
TABLE="200"
SLEEP_INTERVAL=5  # Sleep interval in seconds, can be adjusted

# Function to execute ping in a controlled manner
function check_ping() {
    local ip=$1
    ping -c 1 -W 1 $ip &> /dev/null
    return $?
}

# Function to remove all matching rules
function remove_rules() {
    echo "Removing all rules in table 200 matching $MIKROTIK_IP..."
    while ip rule list | grep -q "to $MIKROTIK_IP lookup $TABLE"; do
        ip rule del to $MIKROTIK_IP/32 table $TABLE &> /dev/null
        echo "Rule removed from table 200."
	sleep 1
    done
    echo "All matching rules removed."
}

# Function to configure the route
configure_route() {
    echo "Attempting to remove all rules from table 200 that match..."
    # Remove all matching rules
    remove_rules

    echo "Checking if Mikrotik is  accessible..."
    # Check if Mikrotik is directly accessible
    if check_ping $MIKROTIK_IP; then
        echo "Ping successful to $MIKROTIK_IP."
    else
        echo "No ping to $MIKROTIK_IP. Checking Tenda..."
        # If Mikrotik is not accessible, add the rule in table 200 to use Tenda
        if ! ip rule list | grep -q "to $MIKROTIK_IP/32 table $TABLE"; then
            ip rule add to $MIKROTIK_IP/32 table $TABLE &> /dev/null
            echo "Rule added in table 200 to route through Tenda."
        else
            echo "The rule in table 200 already existed, nothing was added."
        fi

        echo "Checking if Mikrotik is now accessible through Tenda..."
        # Check if Mikrotik is now accessible through Tenda
        if check_ping $MIKROTIK_IP; then
            echo "Ping successful to $MIKROTIK_IP. Mikrotik accessible through Tenda."
        else
            echo "No ping to $MIKROTIK_IP. Mikrotik not accessible, check connectivity."
        fi
    fi
}

# Infinite loop to continuously monitor
while true; do
    echo "Checking if Mikrotik is already accessible..."
    # Check if Mikrotik is directly accessible
    if ! check_ping $MIKROTIK_IP; then
        echo "No ping to $MIKROTIK_IP. Mikrotik is not accessible, configuring route..."
        # If no ping to Mikrotik, call the function to configure the route
        configure_route
    else
        echo "Ping successful to $MIKROTIK_IP. Mikrotik is already accessible, no changes needed."
    fi

    # Wait a few seconds before the next check
    echo "Waiting $SLEEP_INTERVAL seconds before the next check..."
    sleep $SLEEP_INTERVAL
done
