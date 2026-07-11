import typer
from pathlib import Path
import hashlib
from rich.progress import track
from rich.console import Console
from rich.table import Table
from collections import defaultdict

# Fix for when running as installed package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

app = typer.Typer()
console = Console()

def get_file_hash(filepath: Path):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None

@app.command()
def scan(
    folder: str = typer.Argument(".", help="Folder to scan for duplicates"),
    delete: bool = typer.Option(False, "--delete", help="Delete duplicate files (keeps the first one)")
):
    """Find duplicate files in a folder."""
    console.print(f"[bold blue]📂 Scanning:[/bold blue] {folder}")
    
    folder_path = Path(folder)
    if not folder_path.exists():
        console.print(f"[red]❌ Error:[/red] Folder '{folder}' doesn't exist!")
        return
    
    all_files = [f for f in folder_path.rglob("*") if f.is_file()]
    
    if not all_files:
        console.print("[yellow]⚠️  No files found![/yellow]")
        return
    
    console.print(f"Found [green]{len(all_files)}[/green] files")
    
    size_groups = defaultdict(list)
    for file in track(all_files, description="Grouping by size..."):
        size_groups[file.stat().st_size].append(file)
    
    potential_dupes = {
        size: files 
        for size, files in size_groups.items() 
        if len(files) > 1
    }
    
    if not potential_dupes:
        console.print("[green]✅ No duplicates found![/green]")
        return
    
    console.print(f"Found [yellow]{len(potential_dupes)}[/yellow] size groups")
    
    duplicates = defaultdict(list)
    for size, files in track(potential_dupes.items(), description="Hashing..."):
        hash_groups = defaultdict(list)
        for file in files:
            file_hash = get_file_hash(file)
            if file_hash:
                hash_groups[file_hash].append(file)
        
        for file_hash, dup_files in hash_groups.items():
            if len(dup_files) > 1:
                duplicates[file_hash] = dup_files
    
    if not duplicates:
        console.print("[green]✅ No exact duplicates found![/green]")
        return
    
    total_dupes = sum(len(files) for files in duplicates.values())
    console.print(f"\n[bold red]🔍 Found {total_dupes} duplicates in {len(duplicates)} groups:\n")
    
    for file_hash, files in duplicates.items():
        table = Table(title=f"Hash: {file_hash[:8]}...")
        table.add_column("File", style="cyan")
        table.add_column("Size", style="green")
        
        for f in files:
            size_kb = f.stat().st_size / 1024
            if size_kb > 1024:
                size_mb = size_kb / 1024
                table.add_row(str(f), f"{size_mb:.2f} MB")
            else:
                table.add_row(str(f), f"{size_kb:.2f} KB")
        
        console.print(table)
        console.print("─" * 50)
    
    # ==============================================
    # NEW: Calculate and display space savings
    # ==============================================
    
    # Calculate total space wasted
    total_size = 0
    total_savings = 0
    
    for file_hash, files in duplicates.items():
        # Size of all duplicate files in this group
        group_size = sum(f.stat().st_size for f in files)
        total_size += group_size
        
        # Keep one copy, delete the rest
        # So savings = group_size - size_of_one_file
        group_savings = group_size - files[0].stat().st_size
        total_savings += group_savings
    
    # Display the savings
    if total_savings > 0:
        console.print("")
        if total_savings > 1024 * 1024:  # More than 1 MB
            console.print(f"[bold yellow]💾 Potential space saved: {total_savings / (1024 * 1024):.2f} MB[/bold yellow]")
        elif total_savings > 1024:  # More than 1 KB
            console.print(f"[bold yellow]💾 Potential space saved: {total_savings / 1024:.2f} KB[/bold yellow]")
        else:
            console.print(f"[bold yellow]💾 Potential space saved: {total_savings} bytes[/bold yellow]")
        
        console.print(f"[bold cyan]📊 SUMMARY[/bold cyan]")
        console.print(f"   Total duplicate groups: [yellow]{len(duplicates)}[/yellow]")
        console.print(f"   Total duplicate files: [yellow]{total_dupes}[/yellow]")
        
        if total_savings > 1024 * 1024:
            console.print(f"   Total space wasted: [yellow]{total_savings / (1024 * 1024):.2f} MB[/yellow]")
        elif total_savings > 1024:
            console.print(f"   Total space wasted: [yellow]{total_savings / 1024:.2f} KB[/yellow]")
        else:
            console.print(f"   Total space wasted: [yellow]{total_savings} bytes[/yellow]")
    
    # ==============================================
    # END OF NEW CODE
    # ==============================================
    
    # If delete flag is used, remove duplicates
    if delete:
        console.print("\n[bold yellow]⚠️  DELETE MODE ACTIVATED[/bold yellow]")
        console.print("[yellow]Keeping the first file in each group, deleting the rest...[/yellow]")
        
        deleted_count = 0
        for file_hash, files in duplicates.items():
            # Keep first file, delete the rest
            for file in files[1:]:
                try:
                    file.unlink()
                    console.print(f"[red]🗑️  Deleted:[/red] {file}")
                    deleted_count += 1
                except Exception as e:
                    console.print(f"[red]❌ Error:[/red] {e}")
        
        if deleted_count > 0:
            console.print(f"\n[bold green]✅ Deleted {deleted_count} duplicate files![/bold green]")
            console.print(f"[bold green]💾 Saved {total_savings / (1024 * 1024):.2f} MB of space![/bold green]")
        else:
            console.print("\n[yellow]No files were deleted.[/yellow]")

@app.command()
def hello(name: str = "World"):
    console.print(f"[bold green]Hello {name}! 🚀[/bold green]")

if __name__ == "__main__":
    app()