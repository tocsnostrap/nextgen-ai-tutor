import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ..auth import verify_token
from ....game_manager import game_manager, GAME_TYPES

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class CreateGameRequest(BaseModel):
    game_type: str = "math_race"
    rounds: int = 5
    player_name: str = "Player"
    add_bots: int = 1


class AnswerRequest(BaseModel):
    game_id: str
    answer: int


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


@router.get("/types")
async def get_game_types(user_id: str = Depends(get_current_user_id)):
    return {
        "game_types": [
            {"id": gt_id, "name": gt["name"], "icon": gt["icon"], "time_per_round": gt["time_per_round"]}
            for gt_id, gt in GAME_TYPES.items()
        ]
    }


@router.get("/active")
async def get_active_games(user_id: str = Depends(get_current_user_id)):
    return {"games": game_manager.list_games()}


@router.post("/create")
async def create_game(request: CreateGameRequest, user_id: str = Depends(get_current_user_id)):
    if request.game_type not in GAME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid game type. Choose from: {list(GAME_TYPES.keys())}")

    game = game_manager.create_game(
        game_type=request.game_type,
        creator_id=user_id,
        creator_name=request.player_name,
        rounds=request.rounds,
        add_bots=request.add_bots,
    )

    return {"game": game.to_dict(), "message": "Game created!"}


@router.post("/start/{game_id}")
async def start_game(game_id: str, user_id: str = Depends(get_current_user_id)):
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Only the creator can start the game")
    if game.state != "waiting":
        raise HTTPException(status_code=400, detail="Game already started")

    game.start()

    return {
        "game": game.to_dict(),
        "question": game.get_current_question(),
    }


@router.post("/answer")
async def submit_answer(request: AnswerRequest, user_id: str = Depends(get_current_user_id)):
    game = game_manager.get_game(request.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.state != "playing":
        raise HTTPException(status_code=400, detail="Game is not in progress")
    if user_id not in game.players:
        raise HTTPException(status_code=403, detail="You are not in this game")

    result = game.submit_answer(user_id, request.answer)

    bot_results = game.get_bot_answers()

    all_done = game.all_answered()
    next_question = None
    game_finished = False

    if all_done:
        game.advance_round()
        if game.state == "finished":
            game_finished = True
        else:
            next_question = game.get_current_question()

    correct_answer = game.questions[game.current_round - 2]["answer"] if all_done and game.current_round > 1 else None

    return {
        "result": result,
        "bot_results": bot_results,
        "all_answered": all_done,
        "next_question": next_question,
        "game_finished": game_finished,
        "correct_answer": correct_answer,
        "rankings": game.get_rankings() if game_finished else None,
        "game": game.to_dict(),
    }


@router.get("/results/{game_id}")
async def get_game_results(game_id: str, user_id: str = Depends(get_current_user_id)):
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    rankings = game.get_rankings()
    player_rank = next((r for r in rankings if r["id"] == user_id), None)

    xp_earned = 0
    if player_rank:
        xp_earned = 50
        if player_rank["rank"] == 1:
            xp_earned = 200
        elif player_rank["rank"] == 2:
            xp_earned = 100
        elif player_rank["rank"] == 3:
            xp_earned = 75

    return {
        "game_id": game_id,
        "game_type": game.game_type,
        "rankings": rankings,
        "your_rank": player_rank,
        "xp_earned": xp_earned,
        "total_rounds": len(game.questions),
    }


__all__ = ["router"]
