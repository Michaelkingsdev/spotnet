"""
This module handles user-related API endpoints.
"""
import logging
from decimal import Decimal
from fastapi import APIRouter, HTTPException

from web_app.contract_tools.mixins.dashboard import DashboardMixin
from web_app.db.crud import PositionDBConnector, UserDBConnector
from web_app.api.serializers.transaction import UpdateUserContractRequest
from web_app.api.serializers.user import (
    CheckUserResponse,
    UpdateUserContractResponse,
    GetUserContractAddressResponse,
    GetStatsResponse,
    SubscribeToNotificationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()  # Initialize the router

user_db = UserDBConnector()
position_db = PositionDBConnector()


@router.get(
    "/api/get-user-contract",
    tags=["User Operations"],
    summary="Get user's contract status",
    response_description=(
        "Returns 0 if the user is None or if the contract is not deployed. "
        "Returns the transaction hash if the contract is deployed."
    ),
)
async def get_user_contract(wallet_id: str) -> str:
    """
    Get the contract status of a user.
    :param wallet_id: wallet id
    :return: int
    :raises: HTTPException :return: Dict containing status code and detail
    """
    user = user_db.get_user_by_wallet_id(wallet_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_contract_deployed:
        raise HTTPException(status_code=404, detail="Contract not deployed")
    return user.contract_address


@router.get(
    "/api/check-user",
    tags=["User Operations"],
    summary="Check if user exists and contract status",
    response_model=CheckUserResponse,
    response_description="Returns whether the user's contract is deployed.",
)
async def check_user(wallet_id: str) -> CheckUserResponse:
    """
    This endpoint checks if the user exists, or adds the user to the database if they don't exist,
    and checks whether their contract is deployed.

    ### Parameters:
    - **wallet_id**: The wallet ID of the user.

    ### Returns:
    The contract deployment status
    """

    user = user_db.get_user_by_wallet_id(wallet_id)
    if user and not user.is_contract_deployed:
        return {"is_contract_deployed": False}
    if not user:
        user_db.create_user(wallet_id)
        return {"is_contract_deployed": False}
    return {"is_contract_deployed": True}


@router.post(
    "/api/update-user-contract",
    tags=["User Operations"],
    summary="Update the user's contract",
    response_model=UpdateUserContractResponse,
    response_description="Returns if the contract is updated and deployed.",
)
async def update_user_contract(
    data: UpdateUserContractRequest,
) -> UpdateUserContractResponse:
    """
    This endpoint updates the user's contract.

    ### Parameters:
    - **wallet_id**: The wallet ID of the user.
    - **contract_address**: The contract address being deployed.

    ### Returns:
    The contract deployment status
    """

    user = user_db.get_user_by_wallet_id(data.wallet_id)
    if user:
        user_db.update_user_contract(user, data.contract_address)
        return {"is_contract_deployed": True}
    return {"is_contract_deployed": False}


@router.post(
    "/api/subscribe-to-notification",
    tags=["User Operations"],
    summary="Subscribe user to notifications",
    response_model=SubscribeToNotificationResponse,
    response_description="Returns success status of notification subscription",
)
async def subscribe_to_notification(
    data: SubscribeToNotificationResponse,
) -> SubscribeToNotificationResponse:
    """
    This endpoint subscribes a user to notifications by linking their telegram ID to their wallet.

    ### Parameters:
    - **telegram_id**: The Telegram id of the user.
    - **wallet_id**: The wallet id of the user.

    ### Returns:
    Success status of the subscription.
    """
    user = user_db.get_user_by_wallet_id(data.wallet_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Simulate subscription logic
    success = True  # Placeholder for actual success condition

    if success:
        return {"detail": "User subscribed to notifications successfully"}
    raise HTTPException(status_code=400, detail="Failed to subscribe user to notifications")


@router.get(
    "/api/get-user-contract-address",
    tags=["User Operations"],
    summary="Get user's contract address",
    response_model=GetUserContractAddressResponse,
    response_description="Returns the contract address of the user or None if not deployed.",
)
async def get_user_contract_address(wallet_id: str) -> GetUserContractAddressResponse:
    """
    This endpoint retrieves the contract address of a user.

    ### Parameters:
    - **wallet_id**: User's wallet ID

    ### Returns:
    The contract address or None if it does not exists.
    """

    contract_address = user_db.get_contract_address_by_wallet_id(wallet_id)
    if contract_address:
        return {"contract_address": contract_address}
    return {"contract_address": None}


@router.get(
    "/api/get_stats",
    tags=["User Operations"],
    summary="Get total opened amounts and number of unique users",
    response_model=GetStatsResponse,
    response_description="Total amount for all open positions across all users & \
                          Number of unique users in the database.",
)
async def get_stats() -> GetStatsResponse:
    """
    Retrieves the total amount for open positions converted to USDC
    and the count of unique users.

    ### Returns:
    - total_opened_amount: Sum of amounts for all open positions in USDC.
    - unique_users: Total count of unique users.
    """
    try:
        # Fetch open positions amounts by token
        token_amounts = position_db.get_total_amounts_for_open_positions()

        # Fetch current prices
        current_prices = await DashboardMixin.get_current_prices()

        # Convert all token amounts to USDC
        total_opened_amount = Decimal('0')
        for token, amount in token_amounts.items():
            # Skip if no price available for the token
            if token not in current_prices or 'USDC' not in current_prices:
                logger.warning("No price data available for %s", token)
                continue

            # If the token is USDC, use it directly
            if token == 'USDC':
                total_opened_amount += amount
                continue

            # Convert other tokens to USDC
            # Price is typically in USDC per token
            usdc_price = current_prices[token]
            usdc_equivalent = amount * Decimal(usdc_price)
            total_opened_amount += usdc_equivalent

        unique_users = user_db.get_unique_users_count()
        return GetStatsResponse(
            total_opened_amount=total_opened_amount,
            unique_users=unique_users
        )

    except Exception as e:
        logger.error("Error in get_stats: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e
