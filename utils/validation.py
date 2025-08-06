from functools import wraps

from constants import DOMAINS


def validate_load_args(args):
    """Validate arguments for the 'load' command.

    Parameters
    ----------
    args : list[str]
        Command arguments provided by the user.

    Returns
    -------
    tuple[dict, int]
        The matching domain object from :data:`DOMAINS` and the row number.

    Raises
    ------
    ValueError
        If the arguments are missing or invalid.
    """
    if not args or len(args) < 2:
        raise ValueError("Expected: load <domain> <row>")

    user_domain = " ".join(args[:-1])
    row_arg = args[-1]

    try:
        row_num = int(row_arg)
    except (TypeError, ValueError):
        raise ValueError("Row number must be an integer") from None

    domain = next(
        (
            d
            for d in DOMAINS
            if d.get("full_name", "").lower() == user_domain.lower()
            or user_domain.lower() in [alias.lower() for alias in d.get("aliases", [])]
        ),
        None,
    )
    if not domain:
        raise ValueError(f"Domain '{user_domain}' not found.")

    return domain, row_num


# Mapping of command names to validator functions for future use
VALIDATORS = {
    "load": validate_load_args,
}


def validation_wrapper(func):
    """Factory that applies validation before executing a command function."""

    command_name = func.__name__.replace("cmd_", "", 1)
    validator = VALIDATORS.get(command_name)

    @wraps(func)
    def wrapped(args, state, *f_args, **f_kwargs):
        validated = None
        if validator:
            try:
                validated = validator(args)
            except ValueError as e:
                print(f"❌ {e}")
                from commands.common import print_help_for_command

                return
        return func(args, state, *f_args, validated=validated, **f_kwargs)

    return wrapped
