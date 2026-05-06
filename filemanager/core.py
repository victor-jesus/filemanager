from pathlib import Path
from datetime import datetime
import stat
from collections.abc import Generator

class FileManager():
    """
    A file manager that provides safe file system operations within a root directory.

    Args:
        root_dir: The root directory to operate within. Accepts str or Path.
        dt_template: The str for date format in outputs.
        valid_order_fields: The set that determines the default keys.

    Raises:
        ValueError: If the root directory does not exist.
        NotADirectoryError: If the root path is not a directory.

    Example:
        >>> fm = FileManager('/home/user/documents', '%d-%m-%Y %H:%M:%S', {'name', 'path', 'type', 'size', 'modified_at', 'extension'})
        >>> fm.list_directory(Path('.'))
    """

    def __init__(
        self, 
        root_dir: str | Path, 
        dt_template: str = '%Y-%m-%d %H:%M:%S', 
        valid_order_fields: set | None = None
    ):
        
        self._root_dir = Path(root_dir).resolve()
        self.DT_TEMPLATE = dt_template
        self.VALID_ORDER_FIELDS = (
            valid_order_fields if valid_order_fields is not None 
            else {'name', 'path', 'type', 'size', 'modified_at', 'extension'}
        )
        
        if not self._root_dir.exists():
            raise ValueError("Root directory doesn't exists.")
        if not self._root_dir.is_dir():
            raise NotADirectoryError("Root must be a directory.")

    def _normalize_path(self, path: Path) -> Path:
        """
        Normalizes a path to be absolute, relative to the root directory.

        If the path is relative, it is joined with the root directory.
        If the path is absolute, it is returned as-is before safe resolution.

        Args:
            path: The path to normalize.

        Returns:
            An absolute Path object.
        """
        if not path.is_absolute():
            path = self._root_dir / path
        return path

    def _is_key_valid(self, key: str) -> None:
        """
        Validates if a field name is allowed for ordering.

        Args:
            key: The field name to validate.

        Raises:
            ValueError: If the field is not in VALID_ORDER_FIELDS.
        """
        if key not in self.VALID_ORDER_FIELDS:
            raise ValueError(f"Invalid Field {key}. Fields: {', '.join(self.VALID_ORDER_FIELDS)}")

    def _safe_resolve(self, path: Path) -> Path:
        """
        Resolves a path and ensures it is within the root directory.

        Args:
            path: The path to resolve.

        Returns:
            The resolved absolute Path.

        Raises:
            PermissionError: If the resolved path is outside the root directory.
        """
        path = self._normalize_path(path)
        resolved = path.resolve()
        try:
            resolved.relative_to(self._root_dir)
        except ValueError:
            raise PermissionError("Access denied.")
        return resolved

    def _order_by_key_normalize(self, key: str) -> tuple:
        """
        Parses an order_by key into field name and sort direction.

        A leading '-' indicates descending order.

        Args:
            key: The order_by string, e.g. 'name' or '-name'.

        Returns:
            A tuple of (field: str, reverse: bool).

        Example:
            >>> self._order_by_key_normalize('-name')
            ('name', True)
            >>> self._order_by_key_normalize('name')
            ('name', False)
        """
        reverse = key.startswith('-')
        field = key[1:] if reverse else key
        return field, reverse
    
    def _ensure_exists(self, resolved_path: Path):
        if not resolved_path.exists():
            raise FileNotFoundError("Path does not exists.")
        
    def _ensure_dir(self, resolved_path: Path):
        self._ensure_exists(resolved_path)
        if not resolved_path.is_dir():
            raise NotADirectoryError("Path is not a directory.")
        
    def _get_formatted_date(self, sm_mtime):
        datetime_path = datetime.fromtimestamp(sm_mtime)
        return datetime_path.strftime(self.DT_TEMPLATE)
        
    def _get_metadata(
        self,
        display_path: Path,
        resolved_path: Path,
        stats,
        is_dir: bool
    ) -> dict:
        """
        Build metadata using:
        - display_path → identity (name, path, extension)
        - resolved_path → trusted base (already validated)
        - stats → already fetched (no extra syscall)
        """
        return {
            'name': display_path.name,
            'path': str(display_path.relative_to(self._root_dir)),
            'type': 'directory' if is_dir else 'file',
            'size': stats.st_size,
            'modified_at': self._get_formatted_date(stats.st_mtime),
            'extension': display_path.suffix.lstrip('.')
        }
        
    def get_metadata(self, path: Path):
        """
        Returns metadata for a single file or directory.

        Args:
            path: Path to the file or directory.

        Returns:
            dict: Metadata with the structure:
                {
                    'name': str,
                    'path': str,
                    'type': 'file' | 'directory',
                    'size': int,
                    'modified_at': str,
                    'extension': str
                }

        Raises:
            PermissionError: If the path is outside the root directory.
            FileNotFoundError: If the path does not exist.

        Notes:
            - This is a convenience wrapper around internal metadata extraction.
            - Performs full validation before accessing filesystem metadata.

        Example:
            >>> fm.get_metadata(Path('file.txt'))
        """
        resolved_path = self._safe_resolve(path)
        self._ensure_exists(resolved_path)
        
        stats = resolved_path.stat()
        is_dir = stat.S_ISDIR(stats.st_mode)
        modification_time = stats.st_mtime
        
        #return self._get_metadata(resolresolved_path, stats, is_dir)
    
    def iter_directory(self, 
                    path: Path, 
                    hidden_files: bool = False,
                    symbolic_link: bool = False,
                    recursive: bool = False) -> Generator[dict, None, None]:

        resolved_path = self._safe_resolve(path)
        self._ensure_exists(resolved_path)
        self._ensure_dir(resolved_path)
        
        stack = [resolved_path]
        visited = set()
        
        while stack:
            current_path = stack.pop()
            
            if current_path in visited:
                continue
            
            visited.add(current_path)
            
            try:
                children = current_path.iterdir()
            except (PermissionError, ValueError):
                continue
            
            for child in children:    
                if not hidden_files and child.name.startswith("."):
                    continue
                
                try:                    
                    link_stat = child.lstat()
                except (PermissionError, FileNotFoundError):
                    continue
                
                is_link = stat.S_ISLNK(link_stat.st_mode)
                
                if is_link and not symbolic_link:
                    continue
                
                try:
                    resolved = self._safe_resolve(child)
                except PermissionError:
                    continue
                
                try:
                    st = child.stat() if is_link else link_stat
                except (PermissionError, FileNotFoundError):
                    continue
                
                is_dir = stat.S_ISDIR(st.st_mode)
                
                yield self._get_metadata(
                    display_path=child, 
                    resolved_path=resolved,
                    stats=st,  
                    is_dir=is_dir
                )
                
                if recursive and is_dir:
                    if resolved not in visited:
                        stack.append(resolved)
              
    def search(
        self, 
        name: str | None = None,
        extension: str | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        contains: str | None = None,
        hidden_files: bool = False, 
        recursive: bool = False,
        path: Path | None = None) -> Generator[dict, None, None]:
        """
        Searches for files and directories using multiple filters.

        This method is lazy (generator-based), yielding results incrementally.

        All filters are combined using logical AND.

        Args:
            name: Case-insensitive substring match against the name.
            extension: Exact match for file extension (case-insensitive).
            min_size: Minimum size in bytes (inclusive).
            max_size: Maximum size in bytes (inclusive).
            contains: Case-insensitive substring match across all fields.
            hidden_files: If False, hidden files are excluded.
            recursive: If True, search includes subdirectories.
            path: Directory to search. Defaults to root ('.').

        Yields:
            dict: Metadata dictionary for each matching item.

        Raises:
            PermissionError: If the path is outside the root directory.
            FileNotFoundError: If the path does not exist.
            NotADirectoryError: If the path is not a directory.
            ValueError: If min_size > max_size.

        Notes:
            - Delegates traversal to `iter_directory`.
            - Filtering is performed in-memory per item (no indexing).

        Example:
            >>> list(fm.search(name="report", recursive=True))
            >>> list(fm.search(extension="pdf", min_size=1000))
        """
        if min_size is not None and max_size is not None:
            if min_size > max_size:
                raise ValueError('Minimum size must be lower than maximum size.') 
            
        path = path or Path('.')
        
        predicates = []
        
        if name:
            name_lower = name.lower()
            predicates.append(lambda item: name_lower in item["name"].lower())

        if extension:
            ext_lower = extension.lower().lstrip(".")
            predicates.append(lambda item: item["extension"].lower() == ext_lower)

        if min_size is not None:
            predicates.append(lambda item: item["size"] >= min_size)

        if max_size is not None:
            predicates.append(lambda item: item["size"] <= max_size)
            
        if contains:
            contains_lower = contains.lower()
            predicates.append(
                lambda item: any(contains_lower in str(v).lower() for v in item.values())
            )
            
        for item in self.iter_directory(path, hidden_files, recursive):
            if all(pred(item) for pred in predicates):
                yield item

    def list_directory(
        self, 
        path: Path, 
        recursive: bool = False, 
        hidden_files: bool = False,
        symbolic_link: bool = False,
        order_by: str | None = None) -> dict:
        """
        Lists directory contents with optional recursion and sorting.

        This method materializes all results into memory.

        Args:
            path: Directory to list. Can be relative to root or absolute.
            recursive: If True, includes all subdirectories.
            hidden_files: If False, excludes hidden files.
            order_by: Field to sort by. Prefix with '-' for descending.
                Valid fields: name, path, type, size, modified_at, extension.

        Returns:
            dict:
                {
                    'total': int,
                    'data': [metadata_dict, ...]
                }

        Raises:
            PermissionError: If the path is outside the root directory.
            FileNotFoundError: If the path does not exist.
            NotADirectoryError: If the path is not a directory.
            ValueError: If order_by field is invalid.

        Notes:
            - Uses `iter_directory` internally.
            - Sorting is applied after full materialization.

        Example:
            >>> fm.list_directory(Path('.'))
            >>> fm.list_directory(Path('.'), recursive=True, order_by='-size')
        """
        data = list(self.iter_directory(path, hidden_files=hidden_files, recursive=recursive, symbolic_link=symbolic_link))

        if order_by:
            field, reverse = self._order_by_key_normalize(order_by)
            self._is_key_valid(field)
            data = sorted(
                data,
                key=lambda item: (
                    (item.get(field) is None), 
                    (item.get(field) or 0) if field == 'size' 
                    else (item.get(field) or '')
                ),
                reverse=reverse
            )

        return {
            'total': len(data),
            'data': data
        }
    
if __name__ == '__main__':
    fm = FileManager(Path.cwd())
    test = fm.list_directory(Path('teste'), recursive=True, order_by="-name", symbolic_link=False)
    for item in test['data']:
        print(item)