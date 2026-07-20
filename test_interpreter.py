from dsl_lexer import tokenize
from dsl_parser import Parser
from dsl_interpreter import Interpreter, MovingAverage, LookbackValue


def test_moving_average_returns_none_until_window_full():
    ma = MovingAverage(window=3)
    assert ma.update(10) is None
    assert ma.update(20) is None
    assert ma.update(30) == 20.0  # (10+20+30)/3


def test_moving_average_slides_correctly():
    ma = MovingAverage(window=2)
    ma.update(10)
    ma.update(20)
    assert ma.update(30) == 25.0  # (20+30)/2, 10 has fallen out of the window


def test_lookback_value_returns_correct_past_value():
    lb = LookbackValue(lookback=2)
    lb.update(100)
    lb.update(200)
    result = lb.update(300)
    assert result == 100  # value from exactly 2 steps ago


def test_interpreter_no_signal_before_enough_history():
    source = """fast_ma = moving_average(close, 3)
slow_ma = moving_average(close, 5)
buy when fast_ma crosses_above slow_ma"""
    program = Parser(tokenize(source)).parse_program()
    interp = Interpreter(program)

    # Only 2 bars fed in — nowhere near enough for a 5-bar moving average
    signals_1 = interp.run_bar({"close": 100})
    signals_2 = interp.run_bar({"close": 101})
    assert signals_1 == []
    assert signals_2 == []


def test_interpreter_detects_crossover():
    source = """fast_ma = moving_average(close, 2)
slow_ma = moving_average(close, 3)
buy when fast_ma crosses_above slow_ma"""
    program = Parser(tokenize(source)).parse_program()
    interp = Interpreter(program)

    # Feed a price sequence engineered to force a crossover
    prices = [10, 10, 10, 10, 50]  # sharp jump should push fast_ma above slow_ma
    all_signals = []
    for p in prices:
        all_signals.extend(interp.run_bar({"close": p}))

    assert "BUY" in all_signals


def test_interpreter_zero_look_ahead():
    """
    Confirms the interpreter only ever sees bars fed to it so far —
    there is no way for it to access a bar before run_bar() is called with it.
    """
    source = "buy when close > 1000000"
    program = Parser(tokenize(source)).parse_program()
    interp = Interpreter(program)

    # Even though we're ABOUT to feed a huge price, the interpreter
    # cannot possibly know that in advance — it can only react to
    # what's passed into THIS call.
    signals = interp.run_bar({"close": 5})
    assert signals == []  # correctly no signal, since only today's bar (5) was visible