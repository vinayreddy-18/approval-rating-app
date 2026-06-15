"""Data models for the approval rating app."""


class PoliticianRating:
    def __init__(self, name: str, rating: int):
        self.name = name
        self.rating = rating

    def to_dict(self):
        return {
            'name': self.name,
            'rating': self.rating,
        }
