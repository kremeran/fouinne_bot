from typing import List, Tuple, Dict, Optional, Set, NamedTuple
from enum import Enum, auto
from dataclasses import dataclass
from abc import ABC, abstractmethod
import random
from collections import defaultdict

class Suit(Enum):
    HEARTS = auto()
    DIAMONDS = auto()
    CLUBS = auto()
    SPADES = auto()
    
    def __str__(self):
        return self.name[0]

class CardValue(Enum):
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14
    
    @property
    def points(self) -> int:
        """Calculate point value of card"""
        if self.value == 5:
            return 5
        elif self.value == 10:
            return 10
        elif self.value == 14:
            return 15
        return 0

@dataclass(frozen=True)
class Card:
    suit: Suit
    value: CardValue
    
    def __str__(self):
        return f"{self.value.value}{self.suit}"
    
    @property
    def points(self) -> int:
        return self.value.points

class Bid(NamedTuple):
    player_id: int
    amount: int

@dataclass
class Trick:
    cards: List[Card]
    leader: int
    trump_suit: Suit
    
    @property
    def points(self) -> int:
        return sum(card.points for card in self.cards)
    
    @property
    def winner(self) -> int:
        if not self.cards:
            return self.leader
            
        led_suit = self.cards[0].suit
        winning_card = self.cards[0]
        winner = self.leader
        
        for i, card in enumerate(self.cards[1:], 1):
            player = (self.leader + i) % 4
            # Trump wins over led suit
            if card.suit == self.trump_suit and winning_card.suit != self.trump_suit:
                winning_card = card
                winner = player
            # Higher trump beats lower trump
            elif card.suit == self.trump_suit and winning_card.suit == self.trump_suit:
                if card.value.value > winning_card.value.value:
                    winning_card = card
                    winner = player
            # Higher card of led suit beats lower card of led suit
            elif card.suit == led_suit and winning_card.suit == led_suit:
                if card.value.value > winning_card.value.value:
                    winning_card = card
                    winner = player
                    
        return winner

class Hand:
    def __init__(self, cards: List[Card]):
        self.cards = sorted(cards, key=lambda c: (c.suit.value, c.value.value))
    
    def remove_card(self, card: Card) -> None:
        self.cards.remove(card)
    
    def has_suit(self, suit: Suit) -> bool:
        return any(card.suit == suit for card in self.cards)
    
    def validate_play(self, card: Card, led_suit: Optional[Suit]) -> bool:
        if card not in self.cards:
            return False
        if led_suit and self.has_suit(led_suit) and card.suit != led_suit:
            return False
        return True

class GameState:
    def __init__(self):
        self.scores: Dict[int, int] = {0: 0, 1: 0}
        self.trick_points: Dict[int, int] = defaultdict(int)
        self.played_cards: Set[Card] = set()
        self.current_trick: Optional[Trick] = None
        self.winning_bid: Optional[Bid] = None
        self.trump_suit: Optional[Suit] = None
        
    def add_trick_points(self, winner: int, points: int) -> None:
        self.trick_points[winner % 2] += points
    
    def update_scores(self) -> None:
        if self.winning_bid:
            bid_team = self.winning_bid.player_id % 2
            if self.trick_points[bid_team] >= self.winning_bid.amount:
                self.scores[bid_team] += self.trick_points[bid_team]
            else:
                self.scores[bid_team] -= self.winning_bid.amount
            
            # Non-bidding team always gets their points
            other_team = 1 - bid_team
            self.scores[other_team] += self.trick_points[other_team]

class Bot200(ABC):
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.team = player_id % 2

    @abstractmethod
    def make_bid(self, hand: Hand, game_state: GameState) -> Tuple[int, Suit]:
        """Return bid amount and desired suit (0 for pass)"""
        pass

    @abstractmethod
    def play_card(self, hand: Hand, game_state: GameState) -> Card:
        """Choose card to play from hand"""
        pass

class Deck:
    def __init__(self):
        self.cards = [
            Card(suit, value)
            for suit in Suit
            for value in CardValue
        ]
    
    def deal(self, num_players: int = 4) -> List[Hand]:
        random.shuffle(self.cards)
        hand_size = len(self.cards) // num_players
        return [
            Hand(self.cards[i * hand_size:(i + 1) * hand_size])
            for i in range(num_players)
        ]

class Game200:
    def __init__(self, bot1: Bot200, bot2: Bot200):
        self.bots = [
            bot1,  # Player 0
            bot2,  # Player 1
            Bot200(2),  # Player 2 (copy of bot1)
            Bot200(3)   # Player 3 (copy of bot2)
        ]
        self.game_state = GameState()
        self.deck = Deck()

    def _handle_bidding(self, hands: List[Hand]) -> Optional[Bid]:
        """Conduct bidding round and return winning bid"""
        passes = 0
        current_high_bid = 0
        current_player = 0
        
        while passes < 3:
            bid = self.bots[current_player].make_bid(
                hands[current_player],
                self.game_state
            )
            
            if bid == 0:
                passes += 1
            elif bid > current_high_bid:
                current_high_bid = bid
                winning_bid = Bid(current_player, bid)
                passes = 0
            
            current_player = (current_player + 1) % 4
            
        return winning_bid if current_high_bid > 0 else None

    def play_trick(self, hands: List[Hand], leader: int) -> Trick:
        """Play out a single trick"""
        trick = Trick([], leader, self.game_state.trump_suit)
        current_player = leader
        
        for _ in range(4):
            played_card = self.bots[current_player].play_card(
                hands[current_player],
                self.game_state
            )
            
            led_suit = trick.cards[0].suit if trick.cards else None
            if not hands[current_player].validate_play(played_card, led_suit):
                raise ValueError(f"Invalid play by player {current_player}")
            
            trick.cards.append(played_card)
            hands[current_player].remove_card(played_card)
            self.game_state.played_cards.add(played_card)
            current_player = (current_player + 1) % 4
            
        return trick

    def play_hand(self) -> None:
        """Play a single hand"""
        hands = self.deck.deal()
        self.game_state.trick_points.clear()
        self.game_state.played_cards.clear()
        
        # Bidding phase
        self.game_state.winning_bid = self._handle_bidding(hands)
        if not self.game_state.winning_bid:
            return  # No one bid, redeal
        
        # Set trump suit
        self.game_state.trump_suit = self.bots[self.game_state.winning_bid.player_id].choose_trump(
            hands[self.game_state.winning_bid.player_id],
            self.game_state
        )
        
        # Play tricks
        leader = self.game_state.winning_bid.player_id
        for _ in range(len(hands[0].cards)):
            trick = self.play_trick(hands, leader)
            self.game_state.current_trick = trick
            self.game_state.add_trick_points(trick.winner, trick.points)
            leader = trick.winner
        
        self.game_state.update_scores()

    def play_game(self) -> Tuple[int, int]:
        """Play until one team reaches 200 points"""
        while max(self.game_state.scores.values()) < 200:
            self.play_hand()
            
        winning_team = max(self.game_state.scores.items(), key=lambda x: x[1])[0]
        return winning_team, self.game_state.scores[winning_team]
