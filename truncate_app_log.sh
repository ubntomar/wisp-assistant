#!/bin/bash

# Path to the log file
LOGFILE="/home/orangepi/webserver/app.log"

# Maximum size in bytes (1 MB = 1048576 bytes)
MAXSIZE=1048576

# Debug: Display the current time and start of the script
echo "[$(date)] Starting log truncation script..."

# Check if the file exists
if [ -f "$LOGFILE" ]; then
    # Get the file size
    FILESIZE=$(stat -c%s "$LOGFILE")

    # Debug: Display the current file size
    echo "[$(date)] Current log file size: $FILESIZE bytes"

    # If the file size exceeds the maximum, truncate the file
    if [ $FILESIZE -ge $MAXSIZE ]; then
        echo "[$(date)] Log file size exceeds $MAXSIZE bytes. Truncating log file..."
        > "$LOGFILE"
        
        # Debug: Confirm truncation
        if [ $? -eq 0 ]; then
            echo "[$(date)] Log file truncated successfully."
        else
            echo "[$(date)] Error truncating log file."
        fi

        # Add a message to the log file after truncation
        echo "[$(date)] Log file truncated due to size exceeding 1MB." >> "$LOGFILE"
    else
        echo "[$(date)] Log file size is within the limit. No truncation needed."
    fi
else
    echo "[$(date)] Log file does not exist: $LOGFILE"
fi

# Debug: End of script
echo "[$(date)] Log truncation script completed."

