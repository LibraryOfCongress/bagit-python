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
- **Handles existing BagIt bags** by re-bagging them with fresh checksums and validation

### 🔒 **Data Protection**

- Creates SHA256 and SHA512 checksums for every file
- Validates all files after transfer
- Detects any corruption or missing files
- Keeps original files safe (never modifies them)
- **Automatically excludes system/hidden files** (macOS .DS_Store, ._files, Windows Thumbs.db, desktop.ini, etc.)
- **Cross-platform hidden file detection** for clean, portable bags

### 📊 **Detailed Logging**

- Records every action with timestamps
- Shows success/failure for each folder
- Provides detailed validation error messages for troubleshooting
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
- **Configurable batch processing** for memory-efficient handling of large datasets
- **Space-efficient processing** with automatic temporary file cleanup after each batch

### 🚀 **Performance & Efficiency**

- **Batch processing** to manage memory usage and disk space efficiently
- **Default batch size of 1** for maximum space efficiency (configurable)
- Automatic cleanup of temporary files after each batch
- **Handles existing bags intelligently** by re-bagging with fresh validation
- Processes regular folders and existing bags separately for optimal handling

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

# Process in batches (default is 1 for space efficiency)
python auto_bagit_transfer.py --source "C:\Photos" --destination "D:\Backup" --batch-size 5
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
batch_size = 1

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
| `--batch-size NUMBER`           | Process folders in batches (default: 1 for space efficiency)   |

## What Happens When You Run the Tool?

### Step 1: Preparation

- Checks that source and destination paths exist
- Creates destination folder if needed
- Sets up logging

### Step 2: Folder Discovery

- Scans source directory for folders
- **Identifies existing BagIt bags** and regular folders separately
- Applies your include/exclude filters
- Skips empty folders (unless you say otherwise)
- Shows you what will be processed (regular folders and existing bags)

### Step 3: Batch Processing

- **Processes folders in configurable batches** (default: 1 for space efficiency)
- Creates temporary directory for each batch
- **For regular folders:** Creates clean copy excluding hidden/system files, then bags
- **For existing bags:** Extracts data directory, excludes hidden files, creates fresh bag
- Calculates checksums for all files
- Adds BagIt metadata with processing information

### Step 4: Transfer

- Copies the bag to destination
- Validates the transferred bag
- Confirms all files arrived safely
- Records success or failure

### Step 5: Cleanup & Summary

- **Automatically removes temporary files after each batch**
- Shows detailed transfer summary with separate counts for regular folders and re-bagged items
- Provides success rate statistics
- Saves comprehensive log file with batch processing details

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

## Batch Processing & Space Efficiency

### Why Batch Processing?

The tool uses **batch processing by default** to ensure efficient use of temporary disk space and system resources:

- **Prevents temporary space exhaustion** - Only processes one folder at a time by default
- **Memory efficient** - Doesn't load all folders into memory simultaneously  
- **Automatic cleanup** - Removes temporary files after each batch
- **Handles large datasets** - Can process thousands of folders without running out of space

### How Batch Processing Works

1. **Creates temporary directory** for current batch (e.g., `bagit_batch_1_`)
2. **Processes folders in batch:**
   - Regular folders: Creates clean copy (excluding hidden files) → bags → transfers
   - Existing bags: Extracts data directory → excludes hidden files → creates fresh bag → transfers
3. **Validates each transfer** with detailed error reporting
4. **Cleans up temporary directory** completely before next batch
5. **Moves to next batch** until all folders processed

### Default Space-Efficient Settings

```bash
# Default behavior (batch size = 1, maximum space efficiency)
python auto_bagit_transfer.py --source "SOURCE" --destination "DEST"

# Process multiple folders per batch (if you have more temp space)
python auto_bagit_transfer.py --batch-size 5 --source "SOURCE" --destination "DEST"

# Set default in config.ini
[BAGIT_OPTIONS]
batch_size = 1
```

### Hidden File Exclusion

The tool automatically excludes problematic system/hidden files that can cause validation issues:

**macOS files excluded:**
- `.DS_Store` (Finder metadata)
- `._filename` (resource forks)
- Files starting with `._`

**Windows files excluded:**
- `Thumbs.db` / `thumbs.db` (thumbnail cache)
- `desktop.ini` (folder customization)
- `folder.jpg`, `albumartsmall.jpg` (media metadata)

**General exclusions:**
- Hidden files starting with `.` (except in existing bag structure)

## Troubleshooting

| Problem                      | Solution                                                                |
| ---------------------------- | ----------------------------------------------------------------------- |
| "Python not found"           | Install Python 3.x, ensure it's in PATH                                 |
| "Source path does not exist" | Check path spelling and existence                                       |
| "Permission denied"          | Run as Administrator or check permissions                               |
| "Out of space"               | Default batch size of 1 should prevent this; check available temp space |
| "Bag validation failed"      | Check detailed error in logs; tool now excludes problematic hidden files |

### Cross-Platform Compatibility

**Hidden File Handling:**
The tool now **automatically excludes** problematic system files that previously caused validation issues:

- **macOS:** `.DS_Store`, `._files`, resource forks automatically excluded
- **Windows:** `Thumbs.db`, `desktop.ini`, media cache files automatically excluded  
- **All platforms:** Generic hidden files (starting with `.`) excluded from data

**Benefits:**
- **Clean, portable bags** that work across different operating systems
- **No more validation failures** due to hidden system files
- **Consistent behavior** whether source is Windows, Mac, or Linux

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
A: Yes! Check the destination directory to see which folders transferred successfully, then use `--exclude-folders` to skip completed ones or `--include-folders` to process only remaining ones.

**Q: What about duplicate folder names?**  
A: Tool automatically adds numbers (folder_1, folder_2, etc.)

**Q: Can I transfer to network drives?**  
A: Yes, with proper write permissions.

**Q: How to verify successful transfer?**  
A: Check log for "Success rate: 100.0%" and detailed batch summaries showing successful transfers.

**Q: What happens to existing BagIt bags in my source?**  
A: The tool detects existing bags and re-bags them with fresh checksums and validation, excluding any hidden files that may have been added.

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
**Creates:** BagIt-compliant bags, timestamped log files with batch processing details

### For Large Datasets

```bash
# Default space-efficient processing (recommended)
python auto_bagit_transfer.py --source "SOURCE" --destination "DEST"

# Process multiple folders per batch (if you have temp space)
python auto_bagit_transfer.py --batch-size 5 --source "SOURCE" --destination "DEST"
```

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

_This tool is released under CC0 1.0 Universal (CC0 1.0) Public Domain Dedication, making it freely available for any use._
