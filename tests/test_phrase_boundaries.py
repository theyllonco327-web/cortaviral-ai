import unittest

from app import phrase_boundary_quality


class PhraseBoundaryTests(unittest.TestCase):
    def test_terminal_punctuation_is_a_strong_boundary(self):
        score, reason = phrase_boundary_quality({"text": "Eu descobri o segredo."})
        self.assertEqual(score, 2)
        self.assertEqual(reason, "termina em pontuação")

    def test_trailing_connector_is_flagged_as_incomplete(self):
        score, reason = phrase_boundary_quality(
            {"text": "Eu descobri que", "end": 10.0},
            {"text": "isso funcionava.", "start": 10.2, "end": 12.0},
        )
        self.assertEqual(score, -3)
        self.assertEqual(reason, "possível frase incompleta")

    def test_short_gap_signals_continuing_speech(self):
        score, reason = phrase_boundary_quality(
            {"text": "E foi assim", "end": 10.0},
            {"text": "que aconteceu.", "start": 10.2, "end": 12.0},
        )
        self.assertEqual(score, -2)
        self.assertEqual(reason, "fala continua no trecho seguinte")

    def test_long_pause_is_a_natural_boundary(self):
        score, reason = phrase_boundary_quality(
            {"text": "Esse foi o resultado", "end": 10.0},
            {"text": "final.", "start": 12.0, "end": 14.0},
        )
        self.assertEqual(score, 1)
        self.assertEqual(reason, "pausa natural na fala")


if __name__ == "__main__":
    unittest.main()
