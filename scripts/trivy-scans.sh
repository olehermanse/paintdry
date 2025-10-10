#!/bin/bash

# Base directory containing GitHub repositories
BASE_DIR="mount-state/repos/github.com"

# Check if base directory exists
if [ ! -d "$BASE_DIR" ]; then
    echo "Error: Directory $BASE_DIR does not exist"
    exit 1
fi

# Find all repositories (directories) in the subdirectories
for org_dir in "$BASE_DIR"/*; do
    if [ -d "$org_dir" ]; then
        org_name=$(basename "$org_dir")
        echo "Processing organization: $org_name"
        
        for repo_dir in "$org_dir"/*; do
            if [ -d "$repo_dir" ]; then
                repo_name=$(basename "$repo_dir")
                echo "  Scanning repository: $repo_name"
                
                # Change to repository directory
                cd "$repo_dir" || continue
                
                # Run trivy scan and save output
                trivy fs . --format cyclonedx > trivy.json
                
                if [ $? -eq 0 ]; then
                    echo "    ✓ Scan completed: $(pwd)/trivy.json"
                else
                    echo "    ✗ Scan failed for $org_name/$repo_name"
                fi
                
                # Return to base directory
                cd - > /dev/null
            fi
        done
    fi
done

echo "All scans completed"