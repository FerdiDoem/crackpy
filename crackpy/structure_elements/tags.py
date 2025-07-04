"""Links tags, columns and the information to plot them."""
from typing import List, Dict
from enum import Enum
from dataclasses import dataclass, field


def _ltm_coeff(power: float) -> tuple[float, float, float]:
    """Helper returning Length-Time-Mass exponents for ``MPa m**power``."""
    return (power - 1.0, -2.0, 1.0)

# create a class for the statistics
class CGStatistics(Enum):
    """Enum for the statistics that can be performed on the data."""
    IS = ''
    ABS = 'abs'
    MAX = 'max'
    MIN = 'min'
    DELTA = 'delta'
    SMOOTHIS = 'smooth'
    SMOOTHMAX = 'smooth_max'
    SMOOTHMIN = 'smooth_min'
    SMOOTHDELTA = 'smooth_delta'

    def __str__(self):
        return self.value

    # add a method to convert the Enum to latex
    @staticmethod
    def to_latex(stat: str) -> str:
        """Convert the statistics to latex."""
        stat = str(stat)
        if stat == '':
            return ''
        elif stat == 'abs':
            return r'$abs$'
        elif stat == 'max':
            return r'$\max$'
        elif stat == 'min':
            return r'$\min$'
        elif stat == 'delta':
            return r'$\Delta$'
        elif stat == 'smooth':
            return r'$_{smth}$'
        elif stat == 'smooth_max':
            return r'$\max_{smth}$'
        elif stat == 'smooth_min':
            return r'$\min_{smth}$'
        elif stat == 'smooth_delta':
            return r'$\Delta_{smth}$'
        else:
            raise ValueError(f'Unknown statistic {stat}')

@dataclass
class Tag:
    """Base class for tags. Holds some generic information and defines methods to interact with the Tag subclasses."""
    tag: str = 'Tag'
    crack_tip_x: dict = field(default_factory=lambda: {'tag': 'Crack_tip_x', 'unit': r'$mm$', 'label': r'Crack tip $x_{ct}$'})
    crack_tip_y: dict = field(default_factory=lambda: {'tag': 'Crack_tip_y', 'unit': r'$mm$', 'label': r'Crack tip $y_{ct}$'})
    crack_tip_phi: dict = field(default_factory=lambda: {'tag': 'Crack_tip_phi', 'unit': r'$^o$', 'label': r'Crack tip $\phi_{ct}$'})
    cycles: dict = field(default_factory=lambda: {'tag': 'Cycles', 'unit': r'$-$', 'label': r'Cycles $N$'})
    cracklength_dcpd: dict = field(default_factory=lambda: {'tag': 'Cracklength_dcpd', 'unit': r'$mm$', 'label': r'$a_{dcpd}$'})
    cracklength_vec: dict = field(default_factory=lambda: {'tag': 'Cracklength_vec', 'unit': r'$mm$', 'label': r'$a_{cpy-vec}$'})
    cracklength_cum: dict = field(default_factory=lambda: {'tag': 'Cracklength_cum', 'unit': r'$mm$', 'label': r'$a_{cpy-kum.}$'})
    growth_rate_cracklength_dcpd: dict = field(default_factory=lambda: {'tag': 'Growth_rate_Cracklength_dcpd', 'unit': r'$mm/Zyklus$', 'label': r'$da_{dcpd}/dN$'})
    growth_rate_crack_tip_x: dict = field(default_factory=lambda: {'tag': 'Growth_rate_Crack_tip_x', 'unit': r'$mm/1$',
                                                                   'label': r'Growth rate $da_{PNet\ x}/dN$ '})
    growth_rate_vec: dict = field(default_factory=lambda: {'tag': 'Growth_rate_Cracklength_vec', 'unit': r'$mm/1$', 'label': r'Growth rate $da_{PNet,vec}/dN$'})
    growth_rate_cum: dict = field(default_factory=lambda: {'tag': 'Growth_rate_Cracklength_cum', 'unit': r'$mm/1$', 'label': r'$da_{cpy-kum.}/dN$'})
    K_I_by_Y: dict = field(default_factory=lambda: {'tag': 'SIF_by_Y', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{I,cpy-thr.}$'})
    K_I_ASTM: dict = field(default_factory=lambda: {'tag': 'SIF_ASTM', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{dcpd-ASTM}$'})

    # default str return
    def __str__(self):
        return self.tag

    def get_result_list(self) -> List[str]:
        """Returns a list of all tags."""
        return [getattr(self, key)['tag'] for key in self.__dict__.keys() if key != 'tag']

    def get_result_dict(self) -> Dict[str, str]:
        """Returns a dictionary of all tags."""
        return {getattr(self, key)['tag']: key for key in self.__dict__.keys() if key != 'tag'}

    def get_result_tag(self, result: str) -> str:
        """Returns the tag of a result."""
        return getattr(self, self.get_result_dict()[result])['tag']

    def get_result_unit(self, result: str) -> str:
        """Returns the unit of a result."""
        return getattr(self, self.get_result_dict()[result])['unit']

    def get_param_label(self, result: str) -> str:
        """Returns the label of a result."""
        return getattr(self, self.get_result_dict()[result])['label']

@dataclass
class TagASTM(Tag):
    tag: str = 'ASTM'
    crack_tip_x: dict = None
    crack_tip_y: dict = None
    crack_tip_phi:dict  = None
    cycles: dict = field(default_factory=lambda: {'tag': 'Cycle', 'unit': r'$-$', 'label': r'Cycles $N$'})
    growth_rate_cracklength_dcpd: dict = field(
        default_factory=lambda: {'tag': 'Growth_rate', 'unit': r'$mm/1$',
                                 'label': r'Growth rate $da_{DC-PD}/dN$'})
    K_I: dict = field(default_factory=lambda: {'tag': 'SIF', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{dcpd-ASTM}$'})
    cracklength_dcpd: dict = field(default_factory=lambda: {'tag': 'Cracklength', 'unit': r'$mm$', 'label': r'Crack length $a_{DC-PD}$'})
    cracklength_vec = None
    cracklength_cumm = None
    growth_rate_crack_tip_x = None
    growth_rate_vec = None
    growth_rate_cum = None
    SIF_ASTM = None
    SIF_by_Y = None

@dataclass
class TagANSYS(Tag):
    """Holds the nomenclature for the Tag ANSYS_results."""
    tag: str = 'ANSYS'
    cracklength_dcpd: dict = None
    SIF_ASTM: dict = None
    SIF_by_Y: dict  = None
    K_I_VCCT: dict = field(default_factory=lambda: {'tag': 'K_I_VCCT', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{I,ANSYS-VCCT}$'})
    K_II_VCCT: dict = field(default_factory=lambda: {'tag': 'K_II_VCCT', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{II,ANSYS-VCCT}$'})
    K_III_VCCT: dict = field(default_factory=lambda: {'tag': 'K_III_VCCT', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{III,ANSYS-VCCT}$'})
    K_V_VCCT: dict = field(default_factory=lambda: {'tag': 'K_V_VCCT', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{V,ANSYS-VCCT}$'})
    K_I_SIFS: dict = field(default_factory=lambda: {'tag': 'K_I_SIFS', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{I,ANSYS-SIFS}$'})
    K_II_SIFS: dict = field(default_factory=lambda: {'tag': 'K_II_SIFS', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{II,ANSYS-SIFS}$'})
    K_III_SIFS: dict = field(default_factory=lambda: {'tag': 'K_III_SIFS', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{III,ANSYS-SIFS}$'})
    K_V_SIFS: dict = field(default_factory=lambda: {'tag': 'K_V_SIFS', 'unit': r'$MPa\sqrt{m}$', 'label': r'$K_{V,ANSYS-SIFS}$'})
    T: dict = field(default_factory=lambda: {'tag': 'T', 'unit': r'$MPa$', 'label': r'$T_{ANSYS}$'})


@dataclass
class TagExperimentData(Tag):
    """Holds the nomenclature for the Tag Experiment_Data."""
    tag: str = 'Experiment_data'
    force: dict = field(default_factory=lambda: {'tag': 'Force', 'unit': r'$N$', 'label': r'Force $F$'})
    displacement: dict = field(default_factory=lambda: {'tag': 'Displacement', 'unit': r'$mm$', 'label': r'Displacement $d$'})
    potential: dict = field(default_factory=lambda: {'tag': 'Potential', 'unit': r'$V$', 'label': r'Potential $U$'})
    timestamp: dict = field(default_factory=lambda: {'tag': 'timestamp', 'unit': r'$s$', 'label': r'Time $t$'})

@dataclass
class TagCJPModel(Tag):
    """Holds the nomenclature for the Tag CJP_Model."""
    tag: str = 'CJP_results'
    error: dict = field(default_factory=lambda: {
        'tag': 'Error',
        'unit': r'-',
        'label': r'Error',
        'ltm': (0.0, 0.0, 0.0),
    })
    K_F: dict = field(default_factory=lambda: {
        'tag': 'K_F',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{F,CJP}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_R: dict = field(default_factory=lambda: {
        'tag': 'K_R',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{R,CJP}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_S: dict = field(default_factory=lambda: {
        'tag': 'K_S',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{S,CJP}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II: dict = field(default_factory=lambda: {
        'tag': 'K_II',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{II,CJP}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_eff_Yang: dict = field(default_factory=lambda: {
        'tag': 'K_eff_Yang',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{eff,Yang}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_eff_Nowell: dict = field(default_factory=lambda: {
        'tag': 'K_eff_Nowell',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{eff,Nowell}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T: dict = field(default_factory=lambda: {
        'tag': 'T',
        'unit': r'$MPa$',
        'label': r'$T_{CJP}$',
        'ltm': (-1.0, -2.0, 1.0),
    })

@dataclass
class TagWillimasFitting(Tag):
    """Holds the nomenclature for the Tag Williams_Fitting."""
    tag: str = 'Williams_fit_results'
    orders: tuple[int, ...] = (-3, -2, -1, 0, 1, 2, 3, 4, 5)

    error: dict = field(default_factory=lambda: {
        'tag': 'Error',
        'unit': r'-',
        'label': r'Error',
        'ltm': (0.0, 0.0, 0.0),
    })
    K_I: dict = field(default_factory=lambda: {
        'tag': 'K_I',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{I,Wllms}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II: dict = field(default_factory=lambda: {
        'tag': 'K_II',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{II,Wllms}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_V: dict = field(default_factory=lambda: {
        'tag': 'K_V',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$K_{V,Wllms}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T: dict = field(default_factory=lambda: {
        'tag': 'T',
        'unit': r'$MPa$',
        'label': r'$T_{Wllms}$',
        'ltm': (-1.0, -2.0, 1.0),
    })

    def coeff(self, prefix: str, n: int) -> dict:
        power = 1 - 0.5 * n
        return {
            'tag': f'{prefix}_{n}',
            'unit': fr'$MPa m^{power}$',
            'label': fr'${prefix}_{n}$',
            'ltm': _ltm_coeff(power),
        }

@dataclass
class TagSIFIntegralEvalMean(Tag):
    """Holds the nomenclature for the Tag SIF_Integral. This is the mean over the paths."""
    tag: str = 'SIFs_integral'
    J: dict = field(default_factory=lambda: {
        'tag': 'J_mean',
        'unit': r'$N/mm$',
        'label': r'Mean $J_{PthInt}$',
        'ltm': (0.0, -2.0, 1.0),
    })
    K_J: dict = field(default_factory=lambda: {
        'tag': 'K_J_mean',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean $K_{J,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_I_interac: dict = field(default_factory=lambda: {
        'tag': 'K_I_interac_mean',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean $K_{I,intrc,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II_interac: dict = field(default_factory=lambda: {
        'tag': 'K_II_interac_mean',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean $K_{II,intrc,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T_interac: dict = field(default_factory=lambda: {
        'tag': 'T_interac_mean',
        'unit': r'$MPa$',
        'label': r'Mean $T_{intrc,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })
    K_I_Chen: dict = field(default_factory=lambda: {
        'tag': 'K_I_Chen_mean',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean $K_{I,Chen,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II_Chen: dict = field(default_factory=lambda: {
        'tag': 'K_II_Chen_mean',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean $K_{II,Chen,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T_Chen: dict = field(default_factory=lambda: {
        'tag': 'T_Chen_mean',
        'unit': r'$MPa$',
        'label': r'Mean $T_{Chen,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })
    T_SDM: dict = field(default_factory=lambda: {
        'tag': 'T_SDM_mean',
        'unit': r'$MPa$',
        'label': r'Mean $T_{SDM,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })

@dataclass
class TagSIFIntegralEvalMedian(Tag):
    """Holds the nomenclature for the Tag SIF_Integral. This is the median over the paths."""
    tag: str = 'SIFs_integral'
    J: dict = field(default_factory=lambda: {
        'tag': 'J_median',
        'unit': r'$N/mm$',
        'label': r'Median $J_{PthInt}$',
        'ltm': (0.0, -2.0, 1.0),
    })
    K_J: dict = field(default_factory=lambda: {
        'tag': 'K_J_median',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Median $K_{J,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_I_interac: dict = field(default_factory=lambda: {
        'tag': 'K_I_interac_median',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Median $K_{I,intrc,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II_interac: dict = field(default_factory=lambda: {
        'tag': 'K_II_interac_median',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Median $K_{II,intrc,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T_interac: dict = field(default_factory=lambda: {
        'tag': 'T_interac_median',
        'unit': r'$MPa$',
        'label': r'Median $T_{intrc,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })
    K_I_Chen: dict = field(default_factory=lambda: {
        'tag': 'K_I_Chen_median',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Median $K_{I,Chen,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II_Chen: dict = field(default_factory=lambda: {
        'tag': 'K_II_Chen_median',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Median $K_{II,Chen,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T_Chen: dict = field(default_factory=lambda: {
        'tag': 'T_Chen_median',
        'unit': r'$MPa$',
        'label': r'Median $T_{Chen,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })
    T_SDM: dict = field(default_factory=lambda: {
        'tag': 'T_SDM_median',
        'unit': r'$MPa$',
        'label': r'Median $T_{SDM,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })

@dataclass
class TagSIFIntegralEvalMeanWOoutliers(Tag):
    """Holds the nomenclature for the Tag SIF_Integral. This is the mean over the paths without outliers."""
    tag: str = 'SIFs_integral'
    J: dict = field(default_factory=lambda: {
        'tag': 'J_mean_wo_outliers',
        'unit': r'$N/mm$',
        'label': r'Mean$_{wo\\ outlrs}$ $J_{PthInt}$',
        'ltm': (0.0, -2.0, 1.0),
    })
    K_J: dict = field(default_factory=lambda: {
        'tag': 'K_J_mean_wo_outliers',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean$_{wo\\ outlrs}$ $K_{J,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_I_interac: dict = field(default_factory=lambda: {
        'tag': 'K_I_interac_mean_wo_outliers',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'$\overline{K_I}_{,cpy-Int.}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II_interac: dict = field(default_factory=lambda: {
        'tag': 'K_II_interac_mean_wo_outliers',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean$_{wo\\ outlrs}$ $K_{II,intrc,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T_interac: dict = field(default_factory=lambda: {
        'tag': 'T_interac_mean_wo_outliers',
        'unit': r'$MPa$',
        'label': r'Mean$_{wo\\ outlrs}$ $T_{intrc,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })
    K_I_Chen: dict = field(default_factory=lambda: {
        'tag': 'K_I_Chen_mean_wo_outliers',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean$_{wo\\ outlrs}$ $K_{I,Chen,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    K_II_Chen: dict = field(default_factory=lambda: {
        'tag': 'K_II_Chen_mean_wo_outliers',
        'unit': r'$MPa\sqrt{m}$',
        'label': r'Mean$_{wo\\ outlrs}$ $K_{II,Chen,PthInt}$',
        'ltm': (-0.5, -2.0, 1.0),
    })
    T_Chen: dict = field(default_factory=lambda: {
        'tag': 'T_Chen_mean_wo_outliers',
        'unit': r'$MPa$',
        'label': r'Mean$_{wo\\ outlrs}$ $T_{Chen,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })
    T_SDM: dict = field(default_factory=lambda: {
        'tag': 'T_SDM_mean_wo_outliers',
        'unit': r'$MPa$',
        'label': r'Mean$_{wo\\ outlrs}$ $T_{SDM,PthInt}$',
        'ltm': (-1.0, -2.0, 1.0),
    })



class TagConstructor:
    """Constructs a tag (column name) to look for in the data.
    :param stat: The statistic to use. See CGStatistics.
    :param tag: The tag to use. See Tag.
    :param result: The result to use. See Tag.

    example:
    """
    def __init__(self, stat: str = '', tag: str = '', result: str = ''):
        self.tag = tag
        self.result = result
        self.stat = stat

    def __call__(self):
        str = ''
        if self.stat != '':
            str += f'{self.stat}_'
        if self.tag != '':
            str += f'{self.tag}_'
        if self.result != '':
            str += f'{self.result}'

        # remove trailing underscore
        str = str.rstrip('_').lstrip('_')
        return str

class LabelConstructor:
    """Constructs a label for the data.
    :param tag: The tag to use. See Tag.
    :param unit: If the unit should be included.
    :param short_label: If the label should be shortened. Hence without the description.

    example:
    """
    def __init__(self, tag: dict, unit: bool = True, short_label: bool = True):
        self.tag = tag
        self.unit = unit
        self.short_label = short_label

    def __call__(self):
        str = ''
        if self.tag['label'] != '':
            str += f'{self.tag["label"]}'
            if self.short_label:
                # get the post of the first dollar sign and lstript everything before it
                str = str.lstrip(str[:str.find('$')])
        if self.tag['unit'] != '' and self.unit:
            str += f' [{self.tag["unit"]}]'
        # remove trailing underscore
        str = str.rstrip('_').lstrip('_')
        return str

def test_tagConstructor():
    stats = CGStatistics
    tag = TagSIFIntegralEvalMedian()
    tag_constructor = TagConstructor(tag.tag, tag.J['tag'], stats.SMOOTHMAX)()
    print(tag_constructor)

def test_tagDefaultStr():
    tag = Tag()
    tag2 = TagSIFIntegralEvalMean()
    print(tag)
    print(tag2)
    tag_str = tag
    test_dict = {tag.tag: 'tag1', tag2.tag: 'tag2'}

    pass

def test_labelConstructor():
    tag = TagSIFIntegralEvalMean()
    label_constructor = LabelConstructor(tag.K_J, unit=True, short_label=True)()
    print(label_constructor)

if __name__ == '__main__':
    print('This file contains the settings for the individual statistics performed by the CrackGrowthExaminer class.')
    # test the class
    print(CGStatistics.IS)
    print(CGStatistics.ABS)
    print(CGStatistics.MAX)
    print(CGStatistics.MIN)
    print(CGStatistics.DELTA)
    print(CGStatistics.SMOOTHMAX)
    print(CGStatistics.SMOOTHMIN)
    print(CGStatistics.SMOOTHDELTA)

    print('Testing tag.py')
    test_tagConstructor()
    test_tagDefaultStr()
    test_labelConstructor()









