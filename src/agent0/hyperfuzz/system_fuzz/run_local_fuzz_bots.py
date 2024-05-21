"""Helper function for running random fuzz bots."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, ParamSpec, TypeVar

from fixedpointmath import FixedPoint
from numpy.random._generator import Generator

from agent0 import LocalChain, LocalHyperdrive, PolicyZoo
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive.interactive.hyperdrive_agent import HyperdriveAgent
from agent0.hyperfuzz.system_fuzz.invariant_checks import run_invariant_checks

ONE_HOUR_IN_SECONDS = 60 * 60
ONE_DAY_IN_SECONDS = ONE_HOUR_IN_SECONDS * 24
ONE_YEAR_IN_SECONDS = 52 * 7 * ONE_DAY_IN_SECONDS
ONE_YEAR_IN_HOURS = 52 * 7 * 24

# Fuzz ranges, defined as tuples of (min, max)

INITIAL_LIQUIDITY_RANGE: tuple[float, float] = (10, 100_000)
INITIAL_VAULT_SHARE_PRICE_RANGE: tuple[float, float] = (0.5, 2.5)
MINIMUM_SHARE_RESERVES_RANGE: tuple[float, float] = (0.1, 1)
MINIMUM_TRANSACTION_AMOUNT_RANGE: tuple[float, float] = (0.1, 10)
CIRCUIT_BREAKER_DELTA_RANGE: tuple[float, float] = (0.15, 2)

# Position and checkpoint duration are in units of hours, as
# the `factory_checkpoint_duration_resolution` is 1 hour
POSITION_DURATION_HOURS_RANGE: tuple[int, int] = (91, 2 * ONE_YEAR_IN_HOURS)
CHECKPOINT_DURATION_HOURS_RANGE: tuple[int, int] = (1, 24)

# The initial time stretch APR
INITIAL_TIME_STRETCH_APR_RANGE: tuple[float, float] = (0.005, 0.5)
# The variable rate to set after each episode
VARIABLE_RATE_RANGE: tuple[float, float] = (0, 1)
# How much to advance time between episodes
ADVANCE_TIME_SECONDS_RANGE: tuple[int, int] = (0, ONE_DAY_IN_SECONDS)
# The fee percentage. The range controls all 4 fees
FEE_RANGE: tuple[float, float] = (0.0001, 0.2)

# Special case for checking block to block lp share price
LP_SHARE_PRICE_VARIABLE_RATE_RANGE: tuple[float, float] = (0, 0.1)
LP_SHARE_PRICE_FLAT_FEE_RANGE: tuple[float, float] = (0, 0)
LP_SHARE_PRICE_CURVE_FEE_RANGE: tuple[float, float] = (0, 0)
LP_SHARE_PRICE_GOVERNANCE_LP_FEE_RANGE: tuple[float, float] = (0, 0)
LP_SHARE_PRICE_GOVERNANCE_ZOMBIE_FEE_RANGE: tuple[float, float] = (0, 0)


# pylint: disable=too-many-locals
def generate_fuzz_hyperdrive_config(
    rng: Generator, log_to_rollbar: bool, rng_seed: int, lp_share_price_test: bool
) -> LocalHyperdrive.Config:
    """Fuzz over hyperdrive config.

    Arguments
    ---------
    rng: np.random.Generator
        Random number generator.
    log_to_rollbar: bool
        If True, log errors to rollbar.
    rng_seed: int
        Seed for the rng.
    lp_share_price_test: bool
        If True, uses lp share price test fuzz parameters.

    Returns
    -------
    LocalHyperdrive.Config
        Fuzzed hyperdrive config.
    """
    # Position duration must be a multiple of checkpoint duration
    # To do this, we calculate the number of checkpoints per position
    # and adjust the position duration accordingly.
    position_duration_hours = int(rng.integers(*POSITION_DURATION_HOURS_RANGE))
    checkpoint_duration_hours = int(rng.integers(*CHECKPOINT_DURATION_HOURS_RANGE))

    # Checkpoint duration must be a multiple of `factory_checkpoint_duration_resolution`
    checkpoints_per_position_duration = position_duration_hours // checkpoint_duration_hours
    position_duration_hours = checkpoint_duration_hours * checkpoints_per_position_duration
    # There's a chance the new position duration was truncated to be less than the minimum
    # If that's the case, we use the ceil instead.
    if position_duration_hours < POSITION_DURATION_HOURS_RANGE[0]:
        position_duration_hours = checkpoint_duration_hours * (checkpoints_per_position_duration + 1)

    # Sanity check
    assert POSITION_DURATION_HOURS_RANGE[0] <= position_duration_hours <= POSITION_DURATION_HOURS_RANGE[1]

    # Convert checkpoint duration and position duration to seconds
    position_duration = position_duration_hours * ONE_HOUR_IN_SECONDS
    checkpoint_duration = checkpoint_duration_hours * ONE_HOUR_IN_SECONDS

    initial_time_stretch_apr = FixedPoint(rng.uniform(*INITIAL_TIME_STRETCH_APR_RANGE))

    if lp_share_price_test:
        variable_rate_range = LP_SHARE_PRICE_VARIABLE_RATE_RANGE
        flat_fee_range = LP_SHARE_PRICE_FLAT_FEE_RANGE
        curve_fee_range = LP_SHARE_PRICE_CURVE_FEE_RANGE
        governance_lp_fee_range = LP_SHARE_PRICE_GOVERNANCE_LP_FEE_RANGE
        governance_zombie_fee_range = LP_SHARE_PRICE_GOVERNANCE_ZOMBIE_FEE_RANGE
    else:
        variable_rate_range = VARIABLE_RATE_RANGE
        flat_fee_range = FEE_RANGE
        curve_fee_range = FEE_RANGE
        governance_lp_fee_range = FEE_RANGE
        governance_zombie_fee_range = FEE_RANGE

    # Generate flat fee in terms of APR
    flat_fee = FixedPoint(rng.uniform(*flat_fee_range) * (position_duration / ONE_YEAR_IN_SECONDS))

    return LocalHyperdrive.Config(
        preview_before_trade=True,
        rng=rng,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="localfuzzbots",
        crash_log_level=logging.CRITICAL,
        crash_report_additional_info={"rng_seed": rng_seed},
        # Initial hyperdrive config
        initial_liquidity=FixedPoint(rng.uniform(*INITIAL_LIQUIDITY_RANGE)),
        initial_fixed_apr=initial_time_stretch_apr,
        initial_time_stretch_apr=initial_time_stretch_apr,
        initial_variable_rate=FixedPoint(rng.uniform(*variable_rate_range)),
        minimum_share_reserves=FixedPoint(rng.uniform(*MINIMUM_SHARE_RESERVES_RANGE)),
        minimum_transaction_amount=FixedPoint(rng.uniform(*MINIMUM_TRANSACTION_AMOUNT_RANGE)),
        circuit_breaker_delta=FixedPoint(rng.uniform(*CIRCUIT_BREAKER_DELTA_RANGE)),
        position_duration=position_duration,
        checkpoint_duration=checkpoint_duration,
        curve_fee=FixedPoint(rng.uniform(*curve_fee_range)),
        flat_fee=flat_fee,
        governance_lp_fee=FixedPoint(rng.uniform(*governance_lp_fee_range)),
        governance_zombie_fee=FixedPoint(rng.uniform(*governance_zombie_fee_range)),
    )


# Async runner helper
P = ParamSpec("P")
R = TypeVar("R")


# TODO move this to somewhere that's more general
async def async_runner(
    return_exceptions: bool,
    funcs: list[Callable[P, R]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> list[R]:
    """Helper function that runs a list of passed in functions asynchronously.

    WARNING: this assumes all functions passed in are thread safe, use at your own risk.

    TODO: args and kwargs likely should also be a list for passing in separate arguments.

    Arguments
    ---------
    return_exceptions: bool
        If True, return exceptions from the functions. Otherwise, will throw exception if
        a thread fails.
    funcs: list[Callable[P, R]]
        List of functions to run asynchronously.
    *args: P.args
        Positional arguments for the functions.
    **kwargs: P.kwargs
        Keyword arguments for the functions.

    Returns
    -------
    list[R]
        List of results.
    """
    # We launch all functions in threads using the `to_thread` function.
    # This allows the underlying functions to use non-async waits.

    # Runs all functions passed in and gathers results
    gather_result: list[R | BaseException] = await asyncio.gather(
        *[asyncio.to_thread(func, *args, **kwargs) for func in funcs], return_exceptions=return_exceptions
    )

    # Error checking
    # TODO we can add retries here
    out_result: list[R] = []
    for result in gather_result:
        if isinstance(result, BaseException):
            raise result
        out_result.append(result)

    return out_result


def run_local_fuzz_bots(
    hyperdrive_pool: LocalHyperdrive,
    check_invariance: bool,
    num_random_agents: int | None = None,
    num_random_hold_agents: int | None = None,
    base_budget_per_bot: FixedPoint | None = None,
    eth_budget_per_bot: FixedPoint | None = None,
    slippage_tolerance: FixedPoint | None = None,
    raise_error_on_crash: bool = False,
    raise_error_on_failed_invariance_checks: bool = False,
    invariance_test_epsilon: float | None = None,
    minimum_avg_agent_base: FixedPoint | None = None,
    log_to_rollbar: bool = True,
    run_async: bool = False,
    random_advance_time: bool = False,
    random_variable_rate: bool = False,
    num_iterations: int | None = None,
    lp_share_price_test: bool = False,
) -> None:
    """Runs fuzz bots on a hyperdrive pool.

    Arguments
    ---------
    hyperdrive_pool: Hyperdrive
        The hyperdrive pool to run the bots on.
    check_invariance: bool
        If True, will run invariance checks after each set of trades.
    num_random_agents: int | None, optional
        The number of random agents to create. Defaults to 2.
    num_random_hold_agents: int | None, optional
        The number of random agents to create. Defaults to 2.
    base_budget_per_bot: FixedPoint | None, optional
        The base budget per bot. Defaults to 10_000_000
    eth_budget_per_bot: FixedPoint | None, optional
        The ETH budget per bot. Defaults to 1_000
    slippage_tolerance: FixedPoint | None, optional
        The slippage tolerance. Defaults to 1% slippage
    raise_error_on_crash: bool, optional
        If True, will exit the process if a bot crashes. Defaults to False.
    raise_error_on_failed_invariance_checks: bool, optional
        If True, will exit the process if the pool fails an invariance check. Defaults to False.
    invariance_test_epsilon: float | None, optional
        The epsilon for invariance tests. Defaults to 1e-4
    minimum_avg_agent_base: FixedPoint | None, optional
        The minimum average agent base. Will refund bots if average agent base drops below this.
        Defaults to 1/10 of base_budget_per_bot
    log_to_rollbar: bool, optional
        If True, log errors rollbar. Defaults to True.
    run_async: bool, optional
        If True, will run the bots asynchronously. Defaults to False.
    random_advance_time: bool, optional
        If True, will advance the time randomly between sets of trades. Defaults to False.
    random_variable_rate: bool, optional
        If True, will randomly change the rate between sets of trades. Defaults to False.
    num_iterations: int | None, optional
        The number of iterations to run. Defaults to None (infinite)
    lp_share_price_test: bool, optional
        If True, will test the LP share price. Defaults to False.
    """
    # TODO cleanup
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    # Set defaults
    if num_random_agents is None:
        num_random_agents = 2
    if num_random_hold_agents is None:
        num_random_hold_agents = 2
    if base_budget_per_bot is None:
        base_budget_per_bot = FixedPoint("10_000_000")
    if eth_budget_per_bot is None:
        eth_budget_per_bot = FixedPoint("1_000")
    if slippage_tolerance is None:
        slippage_tolerance = FixedPoint("0.01")  # 1% slippage
    if invariance_test_epsilon is None:
        invariance_test_epsilon = 1e-4
    if minimum_avg_agent_base is None:
        minimum_avg_agent_base = base_budget_per_bot / FixedPoint(10)

    # Initialize agents
    agents: list[HyperdriveAgent] = []
    for _ in range(num_random_agents):
        # Initialize & fund agent using a random private key
        agent: HyperdriveAgent = hyperdrive_pool.init_agent(
            base=base_budget_per_bot,
            eth=eth_budget_per_bot,
            private_key=make_private_key(),
            policy=PolicyZoo.random,
            policy_config=PolicyZoo.random.Config(
                slippage_tolerance=slippage_tolerance,
                trade_chance=FixedPoint("0.8"),
                randomly_ignore_slippage_tolerance=True,
                gas_limit=int(1e6),  # Plenty of gas limit for transactions
            ),
        )
        agents.append(agent)

    for _ in range(num_random_hold_agents):
        agent: HyperdriveAgent = hyperdrive_pool.init_agent(
            base=base_budget_per_bot,
            eth=eth_budget_per_bot,
            private_key=make_private_key(),
            policy=PolicyZoo.random_hold,
            policy_config=PolicyZoo.random_hold.Config(
                slippage_tolerance=slippage_tolerance,
                trade_chance=FixedPoint("0.8"),
                randomly_ignore_slippage_tolerance=True,
                max_open_positions=2_000,
                gas_limit=int(1e6),  # Plenty of gas limit for transactions
            ),
        )
        agents.append(agent)

    # Make trades until the user or agents stop us
    logging.info("Trading...")
    iteration = 0
    while True:
        if num_iterations is not None and iteration >= num_iterations:
            break
        iteration += 1
        # Execute the agent policies
        trades = []
        try:
            if run_async:
                trades = asyncio.run(
                    async_runner(
                        return_exceptions=True,
                        funcs=[agent.execute_policy_action for agent in agents],
                    )
                )
            else:
                trades = [agent.execute_policy_action() for agent in agents]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if raise_error_on_crash:
                raise exc
            # Otherwise, we ignore crashes, we want the bot to keep trading
            # These errors will get logged regardless

        # Logs trades
        logging.debug([[trade.__name__ for trade in agent_trade] for agent_trade in trades])

        # Run invariance checks if flag is set
        if check_invariance:
            latest_block = hyperdrive_pool.interface.get_block("latest")
            latest_block_number = latest_block.get("number", None)
            if latest_block_number is None:
                raise AssertionError("Block has no number.")
            run_invariant_checks(
                latest_block=latest_block,
                interface=hyperdrive_pool.interface,
                test_epsilon=invariance_test_epsilon,
                raise_error_on_failure=raise_error_on_failed_invariance_checks,
                log_to_rollbar=log_to_rollbar,
                lp_share_price_test=lp_share_price_test,
            )

        # Check agent funds and refund if necessary
        assert len(agents) > 0
        average_agent_base = sum(agent.get_wallet().balance.amount for agent in agents) / FixedPoint(len(agents))
        # Update agent funds
        if average_agent_base < minimum_avg_agent_base:
            logging.info("Refunding agents...")
            if run_async:
                asyncio.run(
                    async_runner(
                        return_exceptions=True,
                        funcs=[agent.add_funds for agent in agents],
                        base=base_budget_per_bot,
                        eth=eth_budget_per_bot,
                    )
                )
            else:
                _ = [agent.add_funds(base=base_budget_per_bot, eth=eth_budget_per_bot) for agent in agents]

        if random_advance_time:
            # We only allow random advance time if the chain connected to the pool is a
            # LocalChain object
            if isinstance(hyperdrive_pool.chain, LocalChain):
                # RNG should always exist, config's post_init should always
                # initialize an rng object
                assert hyperdrive_pool.config.rng is not None
                # TODO should there be an upper bound for advancing time?
                random_time = int(hyperdrive_pool.config.rng.integers(*ADVANCE_TIME_SECONDS_RANGE))
                hyperdrive_pool.chain.advance_time(random_time, create_checkpoints=True)
            else:
                raise ValueError("Random advance time only allowed for pools deployed on LocalChain")

        if random_variable_rate:
            if isinstance(hyperdrive_pool, LocalHyperdrive):
                # RNG should always exist, config's post_init should always
                # initialize an rng object
                assert hyperdrive_pool.config.rng is not None
                random_rate = FixedPoint(hyperdrive_pool.config.rng.uniform(*VARIABLE_RATE_RANGE))
                hyperdrive_pool.set_variable_rate(random_rate)
            else:
                raise ValueError("Random variable rate only allowed for LocalHyperdrive pools")
