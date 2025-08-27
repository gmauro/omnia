import hashlib
import pathlib

DEFAULT_BUFSIZE = 4096
HASH_ALGORITHM = "sha256"
HASH_LENGTH = 10


class Hashing:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, algorithm: str = HASH_ALGORITHM, bufsize: int = DEFAULT_BUFSIZE, length: int = HASH_LENGTH):
        self.algorithm = algorithm
        self.bufsize = bufsize
        self.length = length

    def compute_hash(self, fpath: str | pathlib.Path = None, st: str = None) -> str | None:
        """
        Computes file or string hash using the algorithm set in the class.
        Notes:
            - If `fpath` is provided, the hash is computed based on the filename and file content.
            - If `st` is provided, the hash is computed based on the string content.
            - If neither `fpath` nor `st` is provided, the function returns None.

        Args:
            fpath (str): Path to a file for which to compute the hash.
            st (str): String for which to compute the hash.
        Returns:
            str: The hash of the input as a hexadecimal string, or None if neither input is provided.
        """
        match (fpath, st):
            case (None, None):
                return None
            case (None, _):
                hash_value = self.compute_string_hash(st)
            case (_, None):
                match fpath:
                    case str():
                        path = pathlib.Path(fpath)
                    case pathlib.Path():
                        path = fpath
                    case _:
                        raise ValueError("Invalid input type for fpath argument")
                # Compute the hash of the filename
                filename_hash = self.compute_string_hash(path.name)
                # Compute the hash of the file content
                file_content_hash = self.compute_file_hash(path)
                # Bind the filename hash, and the file content hash
                hash_value = self.compute_string_hash(filename_hash + file_content_hash)
            case _:
                raise ValueError("Cannot provide both file path and string")

        return hash_value if self.length is None else hash_value[: self.length] if hash_value else None

    def compute_file_hash(self, path: str | pathlib.Path) -> str:
        """
        Computes the hash of a file using the algorithm function

        Args:
            path: The path to the file for which to compute the hash.
            bufsize (int): The size of the buffer to use when reading the file.

        Returns:
            str: The hexadecimal representation of the hash.
        """
        digest = hashlib.new(self.algorithm)
        with open(path, "rb") as fp:
            s = fp.read(self.bufsize)
            while s:
                digest.update(s)
                s = fp.read(self.bufsize)
        return digest.hexdigest()

    def compute_string_hash(self, st: str) -> str:
        """
        Computes the hash of a string using the algorithm function.

        Args:
            st: The string for which to compute the hash.

        Returns:
            str: The hexadecimal representation of the hash.
        """
        h = hashlib.new(self.algorithm)
        h.update(st.encode("ascii"))
        return h.hexdigest()
