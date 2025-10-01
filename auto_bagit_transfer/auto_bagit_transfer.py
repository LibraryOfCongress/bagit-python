#!/usr/bin/env python3
"""
Automated BagIt Transfer Tool

This script automatically transfers all folders from a source directory to a destination
directory using the BagIt format. Each folder is converted to a bag before transfer.

This work is released under CC0 1.0 Universal (CC0 1.0) Public Domain Dedication.
See: https://creativecommons.org/publicdomain/zero/1.0/

Usage:
    python auto_bagit_transfer.py --source "D:\source\path" --destination "D:\destination\path"
"""

import os
import sys
import argparse
import shutil
import logging
import configparser
import tempfile
from pathlib import Path
from datetime import datetime

try:
    import bagit
except ImportError:
    print("Error: bagit module not found. Installing...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "bagit"])
        import bagit
        print("Successfully installed bagit module.")
    except subprocess.CalledProcessError:
        print("Error: Failed to install bagit module. Please install manually with: pip install bagit")
        sys.exit(1)

def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import bagit  # noqa: F401
    except ImportError:
        missing_deps.append("bagit")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nTo install missing dependencies, run:")
        print("  pip install bagit")
        print("  or")
        print("  pip install -r requirements.txt")
        return False
    
    return True

def load_config(config_file='config.ini'):
    """Load configuration from config file"""
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        config.read(config_file)
        return config
    else:
        # Return default configuration if file doesn't exist
        config['PATHS'] = {
            'source_path': '',
            'destination_path': ''
        }
        config['BAGIT_OPTIONS'] = {
            'checksums': 'sha256,sha512',
            'processes': '4',
            'batch_size': '1'
        }
        config['METADATA'] = {
            'source_organization': 'Auto BagIt Transfer Tool',
            'contact_name': 'Automated Process',
            'bag_software_agent': 'auto_bagit_transfer.py'
        }
        return config

def should_exclude_file(file_path):
    """Check if a file should be excluded from bagging (cross-platform hidden/system files)"""
    filename = file_path.name.lower()
    
    # macOS hidden files
    if file_path.name.startswith('._'):
        return True
    if filename == '.DS_Store':
        return True
    
    # Windows system files
    if filename == 'thumbs.db' or filename == 'Thumbs.db':
        return True
    if filename == 'desktop.ini':
        return True
    if filename == 'folder.jpg':
        return True
    if filename == 'albumartsmall.jpg':
        return True
    
    # General hidden files (starting with dot)
    if file_path.name.startswith('.') and len(file_path.name) > 1:
        return True
    
    return False

def setup_logging():
    """Set up logging configuration"""
    log_filename = f"auto_bagit_transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def validate_paths(source_path, destination_path):
    """Validate source and destination paths"""
    source = Path(source_path)
    destination = Path(destination_path)
    
    if not source.exists():
        raise ValueError(f"Source path does not exist: {source_path}")
    
    if not source.is_dir():
        raise ValueError(f"Source path is not a directory: {source_path}")
    
    # Create destination directory if it doesn't exist
    destination.mkdir(parents=True, exist_ok=True)
    
    return source, destination

def get_folders_to_transfer(source_path, include_folders=None, exclude_folders=None, skip_empty=True):
    """Get list of folders to transfer from source directory"""
    folders = []
    existing_bags = []
    
    for item in source_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check include filter
            if include_folders and item.name not in include_folders:
                continue
            
            # Check exclude filter
            if exclude_folders and item.name in exclude_folders:
                continue
            
            # Check if folder is empty (skip if requested)
            if skip_empty and is_folder_empty(item):
                continue
            
            # Check if it's already a bag
            if is_existing_bag(item) or has_bag_structure(item):
                existing_bags.append(item)
            else:
                folders.append(item)
    
    return folders, existing_bags

def is_folder_empty(folder_path):
    """Check if a folder is empty (no files, only empty subdirectories allowed)"""
    try:
        for item in folder_path.rglob('*'):
            if item.is_file():
                return False
        return True
    except (PermissionError, OSError):
        # If we can't read the folder, assume it's not empty to be safe
        return False

def is_existing_bag(folder_path):
    """Check if a folder is already a valid BagIt bag"""
    try:
        bag = bagit.Bag(str(folder_path))
        return bag.is_valid()
    except Exception:
        return False

def has_bag_structure(folder_path):
    """Check if folder has BagIt structure (even if not valid)"""
    required_files = ['bagit.txt', 'bag-info.txt']
    has_data_dir = (folder_path / 'data').is_dir()
    has_required_files = all((folder_path / f).exists() for f in required_files)
    return has_data_dir and has_required_files

def copy_folder_excluding_hidden(src, dst, logger):
    """Copy folder contents excluding hidden/system files from both Windows and macOS"""
    dst.mkdir(parents=True, exist_ok=True)
    
    for item in src.rglob('*'):
        if item.is_file() and not should_exclude_file(item):
            # Calculate relative path from source
            rel_path = item.relative_to(src)
            dest_file = dst / rel_path
            
            # Create parent directories if needed
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(item, dest_file)
            logger.debug(f"Copied: {rel_path}")
        elif item.is_file():
            logger.debug(f"Excluded: {item.relative_to(src)} (hidden/system file)")

def create_bag_from_folder(folder_path, temp_dir, config, logger):
    """Create a bag from a folder"""
    try:
        logger.info(f"Creating bag for folder: {folder_path.name}")
        
        # Create a temporary copy of the folder for bagging, excluding hidden files
        temp_folder = temp_dir / folder_path.name
        copy_folder_excluding_hidden(folder_path, temp_folder, logger)
        
        # Get configuration values
        checksums = [alg.strip() for alg in config.get('BAGIT_OPTIONS', 'checksums').split(',')]
        processes = config.getint('BAGIT_OPTIONS', 'processes')
        
        # Create bag metadata
        bag_info = {
            'Source-Organization': config.get('METADATA', 'source_organization'),
            'Contact-Name': config.get('METADATA', 'contact_name'),
            'External-Description': f'Bag created from folder: {folder_path.name}',
            'Bagging-Date': datetime.now().strftime('%Y-%m-%d'),
            'Bag-Software-Agent': config.get('METADATA', 'bag_software_agent')
        }
        
        # Create the bag
        bagit.make_bag(
            str(temp_folder),
            bag_info=bag_info,
            checksums=checksums,
            processes=processes
        )
        
        logger.info(f"Successfully created bag for: {folder_path.name}")
        return temp_folder
        
    except Exception as e:
        logger.error(f"Failed to create bag for {folder_path.name}: {str(e)}")
        return None

def rebag_existing_bag(bag_path, temp_dir, config, logger):
    """Re-bag an existing bag by extracting data and creating fresh bag"""
    try:
        logger.info(f"Re-bagging existing bag: {bag_path.name}")
        
        # Validate the existing bag first
        try:
            existing_bag = bagit.Bag(str(bag_path))
            try:
                existing_bag.validate()
                logger.info(f"Existing bag {bag_path.name} is valid")
            except bagit.BagValidationError as e:
                logger.warning(f"Existing bag {bag_path.name} validation failed: {str(e)} - proceeding to re-bag anyway...")

        except Exception as e:
            logger.warning(f"Could not validate existing bag {bag_path.name}: {e}")
        
        # Create temp folder for the new bag
        temp_folder = temp_dir / bag_path.name
        temp_folder.mkdir()
        
        # Copy only the data directory contents (not the bag structure), excluding hidden files
        data_dir = bag_path / 'data'
        if data_dir.exists():
            copy_folder_excluding_hidden(data_dir, temp_folder, logger)
        else:
            logger.warning(f"No data directory found in bag {bag_path.name}")
            return None
        
        # Get configuration values
        checksums = [alg.strip() for alg in config.get('BAGIT_OPTIONS', 'checksums').split(',')]
        processes = config.getint('BAGIT_OPTIONS', 'processes')
        
        # Create new bag metadata (preserve some original info if available)
        bag_info = {
            'Source-Organization': config.get('METADATA', 'source_organization'),
            'Contact-Name': config.get('METADATA', 'contact_name'),
            'External-Description': f'Re-bagged from existing bag: {bag_path.name}',
            'Bagging-Date': datetime.now().strftime('%Y-%m-%d'),
            'Bag-Software-Agent': config.get('METADATA', 'bag_software_agent'),
            'Original-Bag-Name': bag_path.name
        }
        
        # Try to preserve some original metadata
        try:
            original_bag_info_file = bag_path / 'bag-info.txt'
            if original_bag_info_file.exists():
                with open(original_bag_info_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.strip().split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            if key in ['External-Description', 'Source-Organization']:
                                bag_info[f'Original-{key}'] = value
        except Exception as e:
            logger.debug(f"Could not read original bag-info.txt: {e}")
        
        # Create the new bag
        bagit.make_bag(
            str(temp_folder),
            bag_info=bag_info,
            checksums=checksums,
            processes=processes
        )
        
        logger.info(f"Successfully re-bagged: {bag_path.name}")
        return temp_folder
        
    except Exception as e:
        logger.error(f"Failed to re-bag {bag_path.name}: {str(e)}")
        return None

def process_batch(folders_batch, temp_dir, destination_path, config, logger, batch_num, total_batches):
    """Process a batch of folders"""
    logger.info(f"\n=== Processing Batch {batch_num}/{total_batches} ({len(folders_batch)} folders) ===")
    
    batch_successful = 0
    batch_failed = 0
    
    for folder in folders_batch:
        logger.info(f"\n--- Processing folder: {folder.name} ---")
        
        # Create bag
        bag_path = create_bag_from_folder(folder, temp_dir, config, logger)
        
        if bag_path:
            # Transfer bag
            if transfer_bag(bag_path, destination_path, logger):
                batch_successful += 1
            else:
                batch_failed += 1
        else:
            batch_failed += 1
        
        logger.info(f"--- Completed processing: {folder.name} ---")
    
    logger.info(f"=== Batch {batch_num} Summary: {batch_successful} successful, {batch_failed} failed ===\n")
    return batch_successful, batch_failed

def process_existing_bags_batch(bags_batch, temp_dir, destination_path, config, logger, batch_num, total_batches):
    """Process a batch of existing bags"""
    logger.info(f"\n=== Re-bagging Batch {batch_num}/{total_batches} ({len(bags_batch)} existing bags) ===")
    
    batch_successful = 0
    batch_failed = 0
    
    for bag_folder in bags_batch:
        logger.info(f"\n--- Re-bagging existing bag: {bag_folder.name} ---")
        
        # Re-bag the existing bag
        bag_path = rebag_existing_bag(bag_folder, temp_dir, config, logger)
        
        if bag_path:
            # Transfer bag
            if transfer_bag(bag_path, destination_path, logger):
                batch_successful += 1
            else:
                batch_failed += 1
        else:
            batch_failed += 1
        
        logger.info(f"--- Completed re-bagging: {bag_folder.name} ---")
    
    logger.info(f"=== Re-bagging Batch {batch_num} Summary: {batch_successful} successful, {batch_failed} failed ===\n")
    return batch_successful, batch_failed

def transfer_bag(bag_path, destination_path, logger):
    """Transfer the bagged folder to destination"""
    try:
        dest_bag_path = destination_path / bag_path.name
        
        # If destination already exists, create a unique name
        counter = 1
        original_dest = dest_bag_path
        while dest_bag_path.exists():
            dest_bag_path = destination_path / f"{original_dest.name}_{counter}"
            counter += 1
        
        logger.info(f"Transferring bag to: {dest_bag_path}")
        shutil.copytree(bag_path, dest_bag_path)
        
        # Validate the transferred bag with detailed error reporting
        try:
            transferred_bag = bagit.Bag(str(dest_bag_path))
            transferred_bag.validate()  # This will raise if invalid
            logger.info(f"Successfully transferred and validated bag: {dest_bag_path.name}")
            return True
        except bagit.BagValidationError as e:
            logger.error(f"Transferred bag failed validation: {dest_bag_path.name} - Details: {str(e)}")
            
            # Additional debugging for macOS hidden file issues
            data_dir = dest_bag_path / 'data'
            if data_dir.exists():
                logger.debug(f"Files found in data directory of {dest_bag_path.name}:")
                try:
                    for item in data_dir.rglob('*'):
                        if item.is_file():
                            logger.debug(f"  - {item.relative_to(data_dir)}")
                except Exception as debug_e:
                    logger.debug(f"Could not list data directory contents: {debug_e}")
            
            return False
        except Exception as e:
            logger.error(f"Error validating transferred bag {dest_bag_path.name}: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to transfer bag {bag_path.name}: {str(e)}")
        return False

def main():
    """Main function to orchestrate the transfer process"""
    parser = argparse.ArgumentParser(description='Automated BagIt Transfer Tool')
    parser.add_argument('--source', 
                       help='Source directory path (overrides config file)')
    parser.add_argument('--destination',
                       help='Destination directory path (overrides config file)')
    parser.add_argument('--config', default='config.ini',
                       help='Configuration file path (default: config.ini)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be transferred without actually doing it')
    parser.add_argument('--include-folders', nargs='+',
                       help='Only transfer these specific folders (space-separated list)')
    parser.add_argument('--exclude-folders', nargs='+',
                       help='Exclude these folders from transfer (space-separated list)')
    parser.add_argument('--include-empty', action='store_true',
                       help='Include empty folders in transfer (default: skip empty folders)')
    parser.add_argument('--batch-size', type=int, default=1,
                       help='Number of folders to process in each batch (default: 1 for space efficiency)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Use command line arguments if provided, otherwise use config file
    source_path_str = args.source or config.get('PATHS', 'source_path')
    destination_path_str = args.destination or config.get('PATHS', 'destination_path')
    
    if not source_path_str or not destination_path_str:
        print("Error: Source and destination paths must be provided either via command line or config file")
        sys.exit(1)
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting automated BagIt transfer process")
    logger.info(f"Source: {source_path_str}")
    logger.info(f"Destination: {destination_path_str}")
    logger.info(f"Batch size: {args.batch_size} (using small batches for space efficiency)")
    
    try:
        # Validate paths
        source_path, destination_path = validate_paths(source_path_str, destination_path_str)
        
        # Get folders to transfer
        skip_empty = not args.include_empty
        folders_to_transfer, existing_bags = get_folders_to_transfer(source_path, args.include_folders, args.exclude_folders, skip_empty)
        
        # Log empty folders that were skipped
        if skip_empty:
            empty_folders = []
            for item in source_path.iterdir():
                if item.is_dir() and not item.name.startswith('.') and is_folder_empty(item):
                    empty_folders.append(item.name)
            
            if empty_folders:
                logger.info(f"Skipped {len(empty_folders)} empty folders:")
                for folder_name in empty_folders:
                    logger.info(f"  - {folder_name} (empty)")
        
        # Report what was found
        total_items = len(folders_to_transfer) + len(existing_bags)
        if total_items == 0:
            logger.info("No folders found to transfer")
            return
        
        if folders_to_transfer:
            logger.info(f"Found {len(folders_to_transfer)} regular folders to bag:")
            for folder in folders_to_transfer:
                logger.info(f"  - {folder.name}")
        
        if existing_bags:
            logger.info(f"Found {len(existing_bags)} existing bags to re-bag:")
            for bag in existing_bags:
                logger.info(f"  - {bag.name} (existing bag)")
        
        if args.dry_run:
            logger.info("Dry run mode - no actual transfers will be performed")
            return
        
        successful_transfers = 0
        failed_transfers = 0
        
        # Process regular folders in batches
        if folders_to_transfer:
            batch_size = args.batch_size if args.batch_size != 1 else config.getint('BAGIT_OPTIONS', 'batch_size', fallback=1)
            total_batches = (len(folders_to_transfer) + batch_size - 1) // batch_size
            logger.info(f"\nProcessing {len(folders_to_transfer)} regular folders in {total_batches} batches of {batch_size}")
            
            for i in range(0, len(folders_to_transfer), batch_size):
                batch = folders_to_transfer[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                # Create temporary directory for this batch
                temp_dir = Path(tempfile.mkdtemp(prefix=f"bagit_batch_{batch_num}_"))
                logger.info(f"Using temporary directory for batch {batch_num}: {temp_dir}")
                
                try:
                    batch_successful, batch_failed = process_batch(
                        batch, temp_dir, destination_path, config, logger, batch_num, total_batches
                    )
                    successful_transfers += batch_successful
                    failed_transfers += batch_failed
                    
                finally:
                    # Clean up temporary directory after each batch
                    logger.info(f"Cleaning up temporary directory for batch {batch_num}: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Process existing bags in batches
        if existing_bags:
            batch_size = args.batch_size if args.batch_size != 1 else config.getint('BAGIT_OPTIONS', 'batch_size', fallback=1)
            total_batches = (len(existing_bags) + batch_size - 1) // batch_size
            logger.info(f"\nRe-bagging {len(existing_bags)} existing bags in {total_batches} batches of {batch_size}")
            
            for i in range(0, len(existing_bags), batch_size):
                batch = existing_bags[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                # Create temporary directory for this batch
                temp_dir = Path(tempfile.mkdtemp(prefix=f"bagit_rebag_batch_{batch_num}_"))
                logger.info(f"Using temporary directory for re-bagging batch {batch_num}: {temp_dir}")
                
                try:
                    batch_successful, batch_failed = process_existing_bags_batch(
                        batch, temp_dir, destination_path, config, logger, batch_num, total_batches
                    )
                    successful_transfers += batch_successful
                    failed_transfers += batch_failed
                    
                finally:
                    # Clean up temporary directory after each batch
                    logger.info(f"Cleaning up temporary directory for re-bagging batch {batch_num}: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Summary
        total_processed = len(folders_to_transfer) + len(existing_bags)
        logger.info("=== Transfer Summary ===")
        logger.info(f"Regular folders processed: {len(folders_to_transfer)}")
        logger.info(f"Existing bags re-bagged: {len(existing_bags)}")
        logger.info(f"Total items processed: {total_processed}")
        logger.info(f"Successful transfers: {successful_transfers}")
        logger.info(f"Failed transfers: {failed_transfers}")
        if total_processed > 0:
            logger.info(f"Success rate: {(successful_transfers/total_processed*100):.1f}%")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()