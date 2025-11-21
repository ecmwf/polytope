import numpy as np


def flatten_metadata(value):
    return value[0] if isinstance(value, np.ndarray) else value


def find_metadata(metadata_idx, compressed_metadata):
    metadata = {}
    for k, vs in compressed_metadata.items():
        metadata_depth = len(vs.shape)
        relevant_metadata_dxs = metadata_idx[:metadata_depth]
        metadata[k] = vs[relevant_metadata_dxs]
    return metadata
