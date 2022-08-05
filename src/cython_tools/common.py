import re


def parse_input(input_type, default=None, prompt='', regex=None, n_trials=3):
    """
    Parses user input if default value is None, or checks `default` value

    :param input_type: expected variable type: str/float/int
    :param prompt: input prompt
    :param default: if default value is given, the function will skip asking, but will do a type check (but raises immediately without re-asking!)
    :param regex: optional regex for string inputs
    :param n_trials: number of trials before input raises an error
    :return:
    :raise ValueError
    """
    if regex is not None:
        if isinstance(regex, str):
            regex = re.compile(regex, re.MULTILINE)
        else:
            assert isinstance(regex, re.Pattern), f'Expected string or compiled re, got {type(regex)}'

    valid_value = None
    for i in range(n_trials):
        if default is None:
            # Add new line to prompt to make logging output look correct
            if input_type is bool:
                value = input(prompt + ' [y/n] \n')
            else:
                value = input(prompt + '\n')
        else:
            value = default

        if input_type is int:
            try:
                valid_value = int(value)
            except ValueError:
                if default is not None:
                    raise ValueError(f'Argument value is incorrect: {default}, expected integer')
                print(f'Type correct int number value')
                continue
            break
        elif input_type is float:
            try:
                valid_value = float(value)
            except ValueError:
                if default is not None:
                    raise ValueError(f'Argument value is incorrect: {default}, expected float')
                print(f'Type correct float number value')
                continue
            break
        elif input_type is bool:
            try:
                if isinstance(value, str):
                    # Given from console
                    _v = value.lower()
                    if _v == 'y' or _v == 'yes' or _v == '1':
                        valid_value = True
                    elif _v == 'n' or _v == 'no' or _v == '0':
                        valid_value = False
                    else:
                        raise ValueError()
                elif isinstance(value, bool):
                    valid_value = value
                else:
                    raise ValueError(f'unsupported')

                break
            except ValueError:
                if default is not None:
                    raise ValueError(f'Argument value is incorrect: {default}, expected bool')
                print(f'Type correct bool value: y/n, yes/no, 1/0')
                continue
        elif input_type is str:
            if not isinstance(value, str):
                raise ValueError(f'Argument value is incorrect: {default}, expected string')
            if len(value) == 0:
                print(f'Empty string, try again')
                continue

            if regex is not None:
                if not regex.match(value):
                    print(f'Incorrect sting input, expected regex={regex}, no match for {value}')
                    continue

            valid_value = value
            break
        else:
            raise NotImplementedError(f'Unsupported input type: {input_type}')

    if valid_value is None:
        raise ValueError(f'Input validation failed')

    return valid_value
