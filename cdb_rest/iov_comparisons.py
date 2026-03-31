# iov_comparisons.py

from decimal import Decimal


# --- Strategy functions ---

def is_invalid_iov_range_discrete(data):
    """End IOV must be >= start IOV. Equal is allowed (adjacent intervals)."""
    return (
        (data['major_iov_end'] < data['major_iov']) or
        ((data['major_iov_end'] == data['major_iov']) and
         (data['minor_iov_end'] < data['minor_iov']))  # strict < only
    )


def is_invalid_iov_range_continuous(data):
    """End IOV must be strictly greater than start IOV."""
    return (
        (data['major_iov_end'] < data['major_iov']) or
        ((data['major_iov_end'] == data['major_iov']) and
         (data['minor_iov_end'] <= data['minor_iov']))  # <= as before
    )


#def is_conflicting_iov_discrete(piov, major_iov_end, minor_iov_end):
#    return (
#        (piov.major_iov <= major_iov_end) or
#        ((piov.major_iov == major_iov_end) and
#         (piov.minor_iov <= minor_iov_end))
#    )


#def is_conflicting_iov_continous(piov, major_iov_end, minor_iov_end):
#    return (
#        (piov.major_iov < major_iov_end) or
#        ((piov.major_iov == major_iov_end) and
#         (piov.minor_iov < minor_iov_end))
#    )

def is_conflicting_iov_discrete(piov, major_iov_end, minor_iov_end):
    return (
        (piov.major_iov <= major_iov_end) or
        ((piov.major_iov == major_iov_end) and
         ((piov.minor_iov <= minor_iov_end) or (minor_iov_end is None)))
    )


def is_conflicting_iov_continuous(piov, major_iov_end, minor_iov_end):
    return (
        (piov.major_iov < major_iov_end) or
        ((piov.major_iov == major_iov_end) and
         ((piov.minor_iov < minor_iov_end) or (minor_iov_end is None)))
    )

def is_conflicting_iov_end_discrete(piov, major_iov, minor_iov):
    return (
        (piov.major_iov_end >= major_iov) or
        ((piov.major_iov_end == major_iov) and 
         ((piov.minor_iov_end >= minor_iov) or (minor_iov_end is None)))
    )


def is_conflicting_iov_end_continuous(piov, major_iov, minor_iov):
    return (
        (piov.major_iov_end > major_iov) or
        ((piov.major_iov_end == major_iov) and 
         ((piov.minor_iov_end > minor_iov) or (minor_iov_end is None)))
    )


def is_iov_end_inside_discrete(piov, major_iov_end, minor_iov_end):
    return (
        (piov.major_iov_end < major_iov_end) or
        ((piov.major_iov_end == major_iov_end) and
         ((piov.minor_iov_end <= minor_iov_end) or (minor_iov_end is None)))
    )


def is_iov_end_inside_continuous(piov, major_iov_end, minor_iov_end):
    return (
        (piov.major_iov_end < major_iov_end) or
        ((piov.major_iov_end == major_iov_end) and
         ((piov.minor_iov_end < minor_iov_end) or (minor_iov_end is None)))
    )


def compute_comb_iov(major_iov, minor_iov):
    return Decimal(Decimal(major_iov) + Decimal(minor_iov) / 10 ** 19)



# --- Mode config ---

IOV_MODE_CONFIG = {
    'discrete': {
        'next_iov_offset':    1,
        'is_invalid_iov_range':      is_invalid_iov_range_discrete,
        'is_conflicting_iov':        is_conflicting_iov_discrete,
        'is_conflicting_iov_end':    is_conflicting_iov_end_discrete,
        'is_iov_end_inside':         is_iov_end_inside_discrete,   

    },
    'continuous': {
        'next_iov_offset':    0,
        'is_invalid_iov_range':      is_invalid_iov_range_continuous,
        'is_conflicting_iov':        is_conflicting_iov_continuous,
        'is_conflicting_iov_end':    is_conflicting_iov_end_continuous,
        'is_iov_end_inside':         is_iov_end_inside_continuous,

    },
}


def get_iov_config(mode: str) -> dict:
    """
    Returns the IOV strategy config for the given mode.
    Raises ValueError for unknown modes.
    """
    if mode not in IOV_MODE_CONFIG:
        raise ValueError(f"Unknown IOV mode '{mode}'. Choose from: {list(IOV_MODE_CONFIG.keys())}")
    return IOV_MODE_CONFIG[mode]