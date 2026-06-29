"""Module for crack tip information wrapper."""
import logging

logger = logging.getLogger(__name__)



class CrackTipInfo:
    """Wrapper for crack tip information.

    Stores the crack tip position, angle, and compatibility side information.
    `crack_tip_id` is optional because existing handoff files only provide
    `left_or_right`. New workflow code should prefer `crack_tip_id` as the
    durable crack-tip identity and keep `left_or_right` as a legacy label.

    Attributes:
        crack_tip_x: x-coordinate of the crack tip in mm
        crack_tip_y: y-coordinate of the crack tip in mm
        crack_tip_angle: angle of crack path in degrees (0 to 180)
        left_or_right: compatibility side identifier ('left', 'right', 'l', or 'r')
        crack_tip_id: durable crack-tip identity independent of the side label

    Methods:
        * set_manually - manually redefine crack tip information

    """

    def __init__(
            self,
            crack_tip_x: float = None,
            crack_tip_y: float = None,
            crack_tip_angle: float = None,
            left_or_right: str = None,
            crack_tip_id: str = None
    ) -> None:
        """Initialize crack tip info with provided attributes.

        Args:
            crack_tip_x: x-coordinate of the actual crack tip in mm
            crack_tip_y: y-coordinate of the actual crack tip in mm
            crack_tip_angle: angle of crack path between 0 and 180 degrees
            left_or_right: compatibility label such as 'left', 'right', 'l', or 'r'
            crack_tip_id: durable crack-tip identity used by workflow and provenance adapters

        """
        self.crack_tip_x = crack_tip_x
        self.crack_tip_y = crack_tip_y
        self.crack_tip_angle = crack_tip_angle
        self.left_or_right = left_or_right
        self.crack_tip_id = crack_tip_id

        logger.debug(
            "CrackTipInfo initialized: x=%s, y=%s, angle=%s, side=%s, crack_tip_id=%s",
            crack_tip_x,
            crack_tip_y,
            crack_tip_angle,
            left_or_right,
            crack_tip_id,
        )

    def set_manually(self, crack_tip_x: float, crack_tip_y: float,
                     crack_tip_angle: float, left_or_right: str, crack_tip_id: str = None) -> None:
        """Alternatively coordinates may be given externally, e.g. from the crack detection module.

        Args:
            crack_tip_x: x-coordinate of the actual crack tip in mm
            crack_tip_y: y-coordinate of the actual crack tip in mm
            crack_tip_angle: angle of crack path between 0 and 180 degrees
            left_or_right: compatibility label such as 'left', 'right', 'l', or 'r'
            crack_tip_id: durable crack-tip identity used by workflow and provenance adapters

        """
        self.crack_tip_x = crack_tip_x
        self.crack_tip_y = crack_tip_y
        self.crack_tip_angle = crack_tip_angle
        self.left_or_right = left_or_right
        self.crack_tip_id = crack_tip_id

        logger.debug(
            "CrackTipInfo updated manually: x=%s, y=%s, angle=%s, side=%s, crack_tip_id=%s",
            crack_tip_x,
            crack_tip_y,
            crack_tip_angle,
            left_or_right,
            crack_tip_id,
        )
