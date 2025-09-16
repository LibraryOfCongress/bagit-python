# Automated BagIt Transfer Tool - Documentation

## What is this tool?

The Automated BagIt Transfer Tool is a cross-platform Python script that helps you safely move folders from one location to another while ensuring your files don't get corrupted during the transfer. It works on both **Windows** and **Mac** (and Linux too!). It uses the BagIt specification developed by the **Library of Congress** that adds extra protection to your files.

Think of it like putting your files in a secure envelope with a seal - if anything goes wrong during transfer, you'll know about it.

This tool is built on top of the [bagit-python](https://github.com/LibraryOfCongress/bagit-python) library, which is the official Python implementation of the BagIt specification maintained by the Library of Congress.

### 🖥️ **Cross-Platform Compatibility**

- **Windows:** Use `python` command
- **Mac/Linux:** Use `python3` command
- **Same script works everywhere** - no need for different versions!

## What does "BagIt" mean?

BagIt is a hierarchical file packaging format developed by the **Library of Congress** for digital preservation and data transfer. It's like a digital safety wrapper for your files that ensures long-term accessibility and integrity.

The BagIt specification is widely used by libraries, archives, and institutions worldwide for digital preservation. When you "bag" a folder, the tool:

- Creates checksums (digital fingerprints) for every file using industry-standard algorithms
- Adds metadata (information about when and how the bag was created)
- Organizes everything in a standardized format recognized internationally
- Verifies that nothing was lost or corrupted during transfer
- Follows Library of Congress best practices for digital preservation

## Key Features

### 🎯 **Smart Folder Selection**

- Transfer ALL folders from a directory
- Transfer only SPECIFIC folders you choose
- EXCLUDE certain folders you don't want
- Skip empty folders automatically

### 🔒 **Data Protection**

- Creates SHA256 and SHA512 checksums for every file
- Validates all files after transfer
- Detects any corruption or missing files
- Keeps original files safe (never modifies them)

### 📊 **Detailed Logging**

- Records every action with timestamps
- Shows success/failure for each folder
- Provides transfer statistics
- Saves logs for future reference

### 🧪 **Safe Testing**

- Dry-run mode to preview what will happen
- No actual transfers until you're ready
- See exactly which folders will be processed

### ⚙️ **Flexible Configuration**

- Use config files for repeated tasks
- Override settings with command-line options
- Customize metadata and processing options

## Usage

### Basic Commands

```bash
# Windows: use 'python'    |    Mac/Linux: use 'python3'

# Transfer all folders
python auto_bagit_transfer.py --source "C:\Photos" --destination "D:\Backup"

# Transfer specific folders only
python auto_bagit_transfer.py --source "C:\Photos" --destination "D:\Backup" --include-folders "Vacation" "Family"

# Exclude certain folders
python auto_bagit_transfer.py --source "C:\Photos" --destination "D:\Backup" --exclude-folders "Temp" "Screenshots"

# Test first (dry run)
python auto_bagit_transfer.py --source "C:\Photos" --destination "D:\Backup" --dry-run

# Use config file
python auto_bagit_transfer.py
```

### Configuration File

The `config.ini` file allows you to set default paths and options so you don't have to type them every time. This is especially useful for repeated transfers or when you have long file paths.

**What it does:**

- Stores your frequently used source and destination paths
- Sets default BagIt options (checksums, processing threads)
- Saves metadata information for bag creation
- Eliminates need to type long command-line arguments

**How to use it:**
Edit `config.ini` with your preferred settings:

```ini
[PATHS]
source_path = C:\Users\Dell\OneDrive\Pictures
destination_path = D:\1_USA\AICIC\bagit\auto_transfer

[BAGIT_OPTIONS]
checksums = sha256,sha512
processes = 4

[METADATA]
source_organization = My Organization
contact_name = Your Name
```

Once configured, simply run `python auto_bagit_transfer.py` without any arguments to use these settings.

## Command Options

| Option                          | Description                  |
| ------------------------------- | ---------------------------- |
| `--source PATH`                 | Source directory             |
| `--destination PATH`            | Destination directory        |
| `--include-folders NAME1 NAME2` | Only transfer these folders  |
| `--exclude-folders NAME1 NAME2` | Skip these folders           |
| `--dry-run`                     | Preview without transferring |
| `--include-empty`               | Include empty folders        |
| `--config FILE`                 | Use different config file    |

## What Happens When You Run the Tool?

### Step 1: Preparation

- Checks that source and destination paths exist
- Creates destination folder if needed
- Sets up logging

### Step 2: Folder Discovery

- Scans source directory for folders
- Applies your include/exclude filters
- Skips empty folders (unless you say otherwise)
- Shows you what will be processed

### Step 3: Bag Creation (for each folder)

- Creates a temporary copy of the folder
- Calculates checksums for all files
- Adds BagIt metadata
- Creates the bag structure

### Step 4: Transfer

- Copies the bag to destination
- Validates the transferred bag
- Confirms all files arrived safely
- Records success or failure

### Step 5: Cleanup

- Removes temporary files
- Shows transfer summary
- Saves detailed log file

## Output Structure

### BagIt Format

```
MyFolder/
├── bagit.txt                 # Format info
├── bag-info.txt             # Metadata
├── manifest-sha256.txt      # File checksums
├── manifest-sha512.txt      # File checksums
├── tagmanifest-*.txt        # Metadata checksums
└── data/                    # Your original files
```

### Log Files

Creates timestamped logs (e.g., `auto_bagit_transfer_20250904_114137.log`) showing:

- Processing steps and results
- Success/failure for each folder
- Final transfer statistics

## Troubleshooting

| Problem                      | Solution                                  |
| ---------------------------- | ----------------------------------------- |
| "Python not found"           | Install Python 3.x, ensure it's in PATH   |
| "Source path does not exist" | Check path spelling and existence         |
| "Permission denied"          | Run as Administrator or check permissions |
| "Out of space"               | Bags need ~10% more space than originals  |
| "Bag validation failed"      | Check storage/network, retry transfer     |

## Safety & Best Practices

**Safety Features:**

- Never modifies original files
- Automatic validation of all transfers
- Complete audit trail in logs
- Dry-run testing mode

**Best Practices:**

1. Always test with `--dry-run` first
2. Ensure adequate disk space (bags are ~10% larger)
3. Don't interrupt transfers in progress
4. Review log files for any failures

## FAQ

**Q: Can I stop and resume a transfer?**  
A: No, restart from the beginning if interrupted.

**Q: What about duplicate folder names?**  
A: Tool automatically adds numbers (folder_1, folder_2, etc.)

**Q: Can I transfer to network drives?**  
A: Yes, with proper write permissions.

**Q: How to verify successful transfer?**  
A: Check log for "Success rate: 100.0%" and no errors.

## Quick Reference

```bash
# Get help
python auto_bagit_transfer.py --help

# Most common usage
python auto_bagit_transfer.py --source "SOURCE_PATH" --destination "DEST_PATH"

# With specific folders
python auto_bagit_transfer.py --include-folders "Folder1" "Folder2"

# Test first
python auto_bagit_transfer.py --dry-run
```

**Files needed:** `auto_bagit_transfer.py`, `config.ini`  
**Dependencies:** `bagit-python` library (automatically installed)  
**Creates:** BagIt-compliant bags, timestamped log files

## About BagIt and Library of Congress

This tool implements the **BagIt File Packaging Format** (RFC 8493), a specification developed by the Library of Congress and the California Digital Library. BagIt is designed to support storage and transfer of arbitrary digital content in a manner that is both simple and robust.

### Key Benefits of the BagIt Standard:

- **Widely adopted** by libraries, archives, and digital preservation communities
- **Platform independent** - works across different operating systems and storage systems  
- **Self-describing** - bags contain all necessary metadata and validation information
- **Tamper evident** - any changes to files are immediately detectable
- **Future-proof** - based on open standards and simple file formats

### Learn More:

- **BagIt Specification:** [RFC 8493](https://tools.ietf.org/rfc/rfc8493.txt)
- **Library of Congress BagIt:** [https://www.loc.gov/preservation/digital/formats/fdd/fdd000531.shtml](https://www.loc.gov/preservation/digital/formats/fdd/fdd000531.shtml)
- **bagit-python Library:** [https://github.com/LibraryOfCongress/bagit-python](https://github.com/LibraryOfCongress/bagit-python)

---

*This tool is released under CC0 1.0 Universal (CC0 1.0) Public Domain Dedication, making it freely available for any use.*
