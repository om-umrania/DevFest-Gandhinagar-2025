---
title: "Essential Linux Commands"
date: "2024-05-01"
tags: ["linux", "command-line", "terminal", "unix"]
---

# Essential Linux Commands

Linux command line is a powerful tool for system administration, file management, and automation tasks.

## File System Navigation

### Basic Navigation
```bash
# List files and directories
ls

# List with details
ls -l

# List all files including hidden
ls -la

# Change directory
cd /path/to/directory

# Go to home directory
cd ~

# Go to parent directory
cd ..

# Show current directory
pwd

# Create directory
mkdir new_directory

# Remove directory
rmdir empty_directory

# Remove directory with contents
rm -rf directory_name
```

### File Operations
```bash
# Copy file
cp source.txt destination.txt

# Copy directory
cp -r source_dir destination_dir

# Move/rename file
mv old_name.txt new_name.txt

# Remove file
rm filename.txt

# Remove multiple files
rm file1.txt file2.txt file3.txt

# Create empty file
touch filename.txt

# View file contents
cat filename.txt

# View file with line numbers
cat -n filename.txt

# View first 10 lines
head filename.txt

# View last 10 lines
tail filename.txt

# View file with pagination
less filename.txt
```

## File Permissions

### Understanding Permissions
```bash
# View permissions
ls -l filename.txt
# Output: -rw-r--r-- 1 user group 1234 Jan 1 12:00 filename.txt
#         ^ ^ ^ ^
#         | | | +-- Others (read)
#         | | +---- Group (read)
#         | +------ Owner (read, write)
#         +-------- File type (- = file, d = directory)
```

### Changing Permissions
```bash
# Change permissions using numbers
chmod 755 filename.txt

# Change permissions using symbols
chmod u+x filename.txt    # Add execute for owner
chmod g-w filename.txt    # Remove write for group
chmod o+r filename.txt    # Add read for others

# Change ownership
chown user:group filename.txt

# Change group only
chgrp groupname filename.txt
```

## Text Processing

### grep - Search Text
```bash
# Search for text in files
grep "search_term" filename.txt

# Search in multiple files
grep "search_term" *.txt

# Case insensitive search
grep -i "search_term" filename.txt

# Search recursively
grep -r "search_term" directory/

# Show line numbers
grep -n "search_term" filename.txt

# Invert match
grep -v "exclude_term" filename.txt
```

### sed - Stream Editor
```bash
# Replace text
sed 's/old_text/new_text/g' filename.txt

# Replace in file
sed -i 's/old_text/new_text/g' filename.txt

# Delete lines
sed '5d' filename.txt  # Delete line 5

# Print specific lines
sed -n '10,20p' filename.txt  # Lines 10-20
```

### awk - Text Processing
```bash
# Print specific columns
awk '{print $1, $3}' filename.txt

# Print lines with condition
awk '$3 > 100 {print}' filename.txt

# Sum column
awk '{sum += $1} END {print sum}' filename.txt

# Count lines
awk 'END {print NR}' filename.txt
```

## System Information

### System Status
```bash
# Show system information
uname -a

# Show disk usage
df -h

# Show directory size
du -h directory_name

# Show memory usage
free -h

# Show running processes
ps aux

# Show system load
uptime

# Show CPU information
lscpu

# Show memory information
free -h
```

### Process Management
```bash
# Show all processes
ps aux

# Show processes in tree format
pstree

# Kill process by PID
kill 1234

# Kill process by name
killall process_name

# Force kill process
kill -9 1234

# Run process in background
command &

# Show background jobs
jobs

# Bring job to foreground
fg %1
```

## Package Management

### Ubuntu/Debian (apt)
```bash
# Update package list
sudo apt update

# Upgrade packages
sudo apt upgrade

# Install package
sudo apt install package_name

# Remove package
sudo apt remove package_name

# Search packages
apt search search_term

# Show package information
apt show package_name
```

### CentOS/RHEL (yum/dnf)
```bash
# Update packages
sudo yum update

# Install package
sudo yum install package_name

# Remove package
sudo yum remove package_name

# Search packages
yum search search_term

# Show package information
yum info package_name
```

## Network Commands

### Network Configuration
```bash
# Show network interfaces
ip addr show

# Show routing table
ip route show

# Test connectivity
ping google.com

# Show network connections
netstat -tuln

# Show listening ports
ss -tuln

# Download file
wget https://example.com/file.zip

# Download with curl
curl -O https://example.com/file.zip
```

### SSH
```bash
# Connect to remote server
ssh user@hostname

# Connect with specific port
ssh -p 2222 user@hostname

# Copy file to remote server
scp file.txt user@hostname:/path/

# Copy directory to remote server
scp -r directory/ user@hostname:/path/

# Copy from remote server
scp user@hostname:/path/file.txt ./
```

## File Compression

### tar - Archive Tool
```bash
# Create tar archive
tar -cvf archive.tar file1 file2

# Create compressed archive
tar -czvf archive.tar.gz directory/

# Extract archive
tar -xvf archive.tar

# Extract compressed archive
tar -xzvf archive.tar.gz

# List archive contents
tar -tvf archive.tar
```

### zip/unzip
```bash
# Create zip archive
zip archive.zip file1 file2

# Create zip with directory
zip -r archive.zip directory/

# Extract zip archive
unzip archive.zip

# List zip contents
unzip -l archive.zip
```

## Environment Variables

### Working with Environment Variables
```bash
# Show all environment variables
env

# Show specific variable
echo $HOME

# Set variable
export MY_VAR="value"

# Add to PATH
export PATH=$PATH:/new/path

# Make permanent (add to ~/.bashrc)
echo 'export MY_VAR="value"' >> ~/.bashrc
```

## Scripting

### Basic Script
```bash
#!/bin/bash
# This is a comment

echo "Hello, World!"

# Variables
NAME="John"
echo "Hello, $NAME"

# Command substitution
DATE=$(date)
echo "Current date: $DATE"

# Conditional
if [ $1 -gt 10 ]; then
    echo "Number is greater than 10"
else
    echo "Number is 10 or less"
fi

# Loop
for i in {1..5}; do
    echo "Iteration $i"
done
```

### Script Permissions
```bash
# Make script executable
chmod +x script.sh

# Run script
./script.sh

# Run with arguments
./script.sh arg1 arg2
```

## Best Practices

### Command Line Tips
- Use tab completion
- Use history with Ctrl+R
- Use aliases for common commands
- Use wildcards for file operations
- Always backup important data

### Security
- Use strong passwords
- Limit sudo access
- Keep system updated
- Monitor system logs
- Use firewall rules
