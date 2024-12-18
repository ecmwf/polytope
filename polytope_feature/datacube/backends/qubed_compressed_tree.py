import json
from collections import defaultdict
from pathlib import Path

Tree = dict[str, "Tree"]


class RefcountedDict(dict[str, int]):
    refcount: int = 1

    def __repr__(self):
        return f"RefcountedDict(refcount={self.refcount}, {super().__repr__()})"

    def __hash__(self):
        return hash(tuple(sorted(self.items())))


class CompressedTree():
    """
    A implementation of a compressed tree that supports lookup, insertion, deletion and caching.
    The caching means that identical subtrees are stored only once, saving memory
    This is implemented internal by storing all subtrees in a global hash table

    """
    cache: dict[int, RefcountedDict]
    tree: RefcountedDict

    def _add_to_cache(self, level: RefcountedDict) -> int:
        "Add a level {key -> hash} to the cache"
        h = hash(level)
        if h not in self.cache:
            # Increase refcounts of the child nodes
            for child_h in level.values():
                self.cache[child_h].refcount += 1
            self.cache[h] = RefcountedDict(level)
        else:
            self.cache[h].refcount += 1
        return h

    def _replace_in_cache(self, old_h, level: RefcountedDict) -> int:
        """
        Replace the object at old_h with a different object level
        If the objects this is a no-op
        """
        # Start by adding the new object to the cache
        new_h = self._add_to_cache(level)

        # Now check if the old object needs to be garbage collected
        self._decrease_refcount(old_h)

        return new_h

    def _decrease_refcount(self, h: int):
        self.cache[h].refcount -= 1
        if self.cache[h].refcount == 0:
            # Recursively decrease refcounts of child nodes
            for child_h in self.cache[h].values():
                self._decrease_refcount(child_h)
            del self.cache[h]

    def cache_tree(self, tree: Tree) -> int:
        "Insert the given tree  (dictonary of dictionaries) (all it's children, recursively) into the hash table and return the hash key"
        level = RefcountedDict({k: self.cache_tree(v) for k, v in tree.items()})
        return self._add_to_cache(level)

    def _cache_path(self, path: list[str]) -> int:
        "Treat path = [x, y, z...] like {x : {y : {z : ...}}} and cache that"
        if not path:
            return self.empty_hash
        k, *rest = path
        return self._add_to_cache(RefcountedDict({k: self._cache_path(rest)}))

    def reconstruct(self, max_depth=None) -> dict[str, dict]:
        "Reconstruct the tree as a normal nested dictionary"
        def reconstruct_node(h: int, depth: int) -> dict[str, dict]:
            if max_depth is not None and depth > max_depth:
                return {}
            return {k: reconstruct_node(v, depth+1) for k, v in self.cache[h].items()}
        return reconstruct_node(self.root_hash, 0)

    def reconstruct_compressed(self) -> dict[str, dict]:
        "Reconstruct the tree as a normal nested dictionary"
        def reconstruct_node(h: int) -> dict[str, dict]:
            dedup: dict[int, set[str]] = defaultdict(set)
            for k, h2 in self.cache[h].items():
                dedup[h2].add(k)

            return {"/".join(keys): reconstruct_node(h) for h, keys in dedup.items()}
        return reconstruct_node(self.root_hash)

    def reconstruct_compressed_ecmwf_style(self, max_depth=None, from_node=None) -> dict[str, dict]:
        "Reconstruct the tree as a normal nested dictionary"
        def reconstruct_node(h: int, depth: int) -> dict[str, dict]:
            if max_depth is not None and depth > max_depth:
                return {}
            dedup: dict[tuple[int, str], set[str]] = defaultdict(set)
            for k, h2 in self.cache[h].items():
                key, value = k.split("=")
                dedup[(h2, key)].add(value)

            return {f"{key}={','.join(values)}": reconstruct_node(h, depth=depth+1) for (h, key), values in dedup.items()}
        return reconstruct_node(from_node or self.root_hash, depth=0)

    def __init__(self, tree: Tree):
        self.cache = {}
        self.empty_hash = hash(RefcountedDict({}))

        # Recursively cache the tree
        self.root_hash = self.cache_tree(tree)

        # Keep a reference to the root of the tree
        self.tree = self.cache[self.root_hash]

    def lookup(self, keys: tuple[str, ...]) -> tuple[bool, tuple[str, ...]]:
        """
        Lookup a subtree in the tree
        Returns success, path
        if success == True it means the path got to the bottom of the tree and path will be equal to keys
        if success == False, path will holds the keys that were found
        """
        loc = self.tree
        for i, key in enumerate(keys):
            if key in loc:
                h = loc[key]  # get the hash of the subtree
                loc = self.cache[h]  # get the subtree
            else:
                return False, keys[:i], h
        return True, keys, h

    def keys(self, keys: tuple[str, ...] = ()):
        loc = self.tree
        for i, key in enumerate(keys):
            if key in loc:
                h = loc[key]  # get the hash of the subtree
                loc = self.cache[h]  # get the subtree
            else:
                return None
        return list(loc.keys())

    def multi_match(self, request: dict[str, list[str]], loc=None):
        if not loc:
            return {"_END_": {}}
        if loc is None:
            loc = self.tree
        matches = {}
        for request_key, request_values in request.items():
            for request_value in request_values:
                meta_key = f"{request_key}={request_value}"
                if meta_key in loc:
                    new_loc = self.cache[loc[meta_key]]
                    matches[meta_key] = self.multi_match(request, new_loc)

        if not matches:
            return {k: {} for k in loc.items()}
        return matches

    def _insert(self, old_h: int, tree: RefcountedDict, keys: tuple[str, ...]) -> int:
        "Insert keys in the subtree and return the new hash of the subtree"
        key, *rest = keys
        assert old_h in self.cache

        # Adding a new branch to the tree
        if key not in tree:
            new_tree = RefcountedDict(tree | {key: self._cache_path(rest)})

        else:
            # Make a copy of the tree and update the subtree
            new_tree = RefcountedDict(tree.copy())
            subtree_h = tree[key]
            subtree = self.cache[subtree_h]
            new_tree[key] = self._insert(subtree_h, subtree, tuple(rest))

        # no-op if the hash hasn't changed
        new_h = self._replace_in_cache(old_h, new_tree)
        return new_h

    def insert(self, keys: tuple[str, ...]):
        """
        Insert a new branch into the compressed tree
        """
        already_there, path = self.lookup(keys)
        if already_there:
            return
        # Update the tree
        self.root_hash = self._insert(self.root_hash, self.tree, keys)
        self.tree = self.cache[self.root_hash]

    def insert_tree(self, subtree: Tree):
        """
        Insert a whole tree into the compressed tree.
        """
        self.root_hash = self._insert_tree(self.root_hash, self.tree, subtree)
        self.tree = self.cache[self.root_hash]

    def _insert_tree(self, old_h: int, tree: RefcountedDict, subtree: Tree) -> int:
        """
        Recursively insert a subtree into the compressed tree and return the new hash.
        """
        assert old_h in self.cache

        # Make a copy of the tree to avoid modifying shared structures
        new_tree = RefcountedDict(tree.copy())
        for key, sub_subtree in subtree.items():
            if key not in tree:
                # Key is not in current tree, add the subtree
                # Cache the subtree rooted at sub_subtree
                subtree_h = self.cache_tree(sub_subtree)
                new_tree[key] = subtree_h
            else:
                # Key is in tree, need to recursively merge
                # Get the hash and subtree from the current tree
                child_h = tree[key]
                child_tree = self.cache[child_h]
                # Recursively merge
                new_child_h = self._insert_tree(child_h, child_tree, sub_subtree)
                new_tree[key] = new_child_h

        # Replace the old hash with the new one in the cache
        new_h = self._replace_in_cache(old_h, new_tree)
        return new_h

    def save(self, path: Path):
        "Save the compressed tree to a file"
        with open(path, "w") as f:
            json.dump({
                "cache": {k: {"refcount": v.refcount, "dict": v} for k, v in self.cache.items()},
                "root_hash": self.root_hash
            }, f)

    @classmethod
    def load(cls, path: Path) -> "CompressedTree":
        "Load the compressed tree from a file"
        with open(path) as f:
            data = json.load(f)
        return cls.from_json(data)

    @classmethod
    def from_json(cls, data: dict) -> "CompressedTree":
        c = CompressedTree({})
        c.cache = {}
        for k, v in data["cache"].items():
            c.cache[int(k)] = RefcountedDict(v["dict"])
            c.cache[int(k)].refcount = v["refcount"]

        c.root_hash = data["root_hash"]
        c.tree = c.cache[c.root_hash]
        return c
