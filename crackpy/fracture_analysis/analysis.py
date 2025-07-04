import warnings

import numpy as np
import rich.progress as progress_rich

from crackpy.fracture_analysis.data_processing import InputData, CrackTipInfo
from crackpy.fracture_analysis.line_integration import (
    IntegralProperties,
    calculate_line_integral,
)
from crackpy.fracture_analysis.optimization import Optimization, OptimizationProperties
from crackpy.structure_elements.data_files import Nodemap
from crackpy.structure_elements.material import Material
from crackpy.structure_elements.results import (
    CJPResults,
    SIFsIntegralMeanResults,
    SIFsIntegralMedianResults,
    SIFsIntegralMeanwoOutlierResults,
    _create_williams_model,
)


class FractureAnalysis:
    """Fracture analysis of a single DIC nodemap.

    The class is able to calculate

    - J-integral
    - K_I and K_II with the interaction integral
    - T-stress with the interaction integral
    - higher-order terms (HOSTs and HORTs) w/ fitting method (ODM)
    - K_F, K_R, K_S, K_II and T w/ the CJP model
    - (BETA) T-stress with the Bueckner-Chen integral
    - (BETA) higher-order terms (HOSTs and HORTs) w/ Bueckner-integral

    Methods:
        * run - run fracture analysis with the provided data

    """

    def __init__(
            self,
            material: Material,
            nodemap: Nodemap | str,
            data: InputData,
            crack_tip_info: CrackTipInfo,
            integral_properties: IntegralProperties | None = IntegralProperties(),
            optimization_properties: OptimizationProperties | None = OptimizationProperties()
    ):
        """Initialize FractureAnalysis class arguments.

        Args:
            material: obj of class Material, material parameters and laws
            nodemap: obj of class Nodemap or filename of file with exported Aramis-DIC data
            data: obj of class InputData, imported data from nodemap_file
            crack_tip_info: obj of class CrackTipInfo, crack tip information (i.e. x,y coordinates, angle, etc.)
            integral_properties: IntegralProperties or None,
                                 wrapper for specification of line integral properties
                                 If None, Bueckner-Chen integral is not calculated.
            optimization_properties: OptimizationProperties or None,
                                     If None, optimization / fitting is not performed.
        """
        self.material = material
        self.nodemap_file = nodemap.name if isinstance(nodemap, Nodemap) else nodemap
        self.data = data
        self.crack_tip = crack_tip_info

        self.optimization_properties = optimization_properties
        if self.optimization_properties is not None:
            self.optimization_properties.ensure_defaults(self.crack_tip.crack_tip_x)

            self.optimization = Optimization(data=self.data,
                                             options=self.optimization_properties,
                                             material=self.material)
            
            self._init_optimizaton_results()

        self.integral_properties = integral_properties
        if self.integral_properties is not None:
            self.integral_properties.ensure_defaults()

            self._init_integral_results()

    def _init_optimizaton_results(self):
        """Initialize variables used for storing optimization evaluation results."""
        # Initialization of optimization output
        self.cjp_coeffs = None
        self.res_cjp = None
        self.williams_coeffs = None
        self.williams_fit_a_n = None
        self.williams_fit_b_n = None
        self.sifs_fit = None
        
    
    def _init_integral_results(self):
        """Initialize lists used for storing integral evaluation results."""
        self.results = []
        self.williams_int_a_n = []
        self.williams_int_b_n = []
        self.williams_int = []
        self.sifs_int = None
        self.int_sizes = []
        self.integration_points = []
        self.tick_sizes = []
        self.num_of_path_nodes = []

    def run(self, progress='off', task_id=None):
        """Run fracture analysis with the provided data, crack_tip_info, and integral_properties.
        Results are stored as class instance attributes 'results', 'sifs', 'int_sizes', and 'path_nodes'.

        Args:
            progress: progress bar object handle (handed-over automatically during pipeline, not needed for single run)
            task_id: task id for progress bar (handed-over automatically during pipeline, not needed for single run)

        """
        if self.optimization_properties is not None:
            self._run_cjp_optimization()
            self._run_williams_optimization()

        if self.integral_properties is not None:
            self._run_line_integrals(progress, task_id)

    def _run_cjp_optimization(self) -> None:
        """Perform CJP optimization and store results."""
        try:
            cjp_results = self.optimization.optimize_cjp_displacements()

            self.cjp_coeffs = cjp_results.x
            A_r, B_r, B_i, C, E = self.cjp_coeffs

            # from Christopher et al. (2013) "Extension of the CJP model to mixed mode I and mode II" formulas 4-8
            K_F = np.sqrt(np.pi / 2) * (A_r - 3 * B_r - 8 * E)
            K_R = -4 * np.sqrt(np.pi / 2) * (2 * B_i + E * np.pi)
            K_S = -np.sqrt(np.pi / 2) * (A_r + B_r)
            K_II = 2 * np.sqrt(2 * np.pi) * B_i
            T = -C
            # m to mm
            K_F /= np.sqrt(1000)
            K_R /= np.sqrt(1000)
            K_S /= np.sqrt(1000)
            K_II /= np.sqrt(1000)

            self.res_cjp = CJPResults(
                error=cjp_results.cost,
                K_F=K_F,
                K_R=K_R,
                K_S=K_S,
                K_II=K_II,
                K_eff_Yang=np.nan,
                K_eff_Nowell=np.nan,
                T=T,
            )

        except Exception:
            print('CJP optimization failed.')
            self.res_cjp = CJPResults(
                error=np.nan,
                K_F=np.nan,
                K_R=np.nan,
                K_S=np.nan,
                K_II=np.nan,
                K_eff_Yang=np.nan,
                K_eff_Nowell=np.nan,
                T=np.nan,
            )

    def _run_williams_optimization(self) -> None:
        """Perform Williams optimization and store results."""
        try:
            williams_results = self.optimization.optimize_williams_displacements()
            self.williams_coeffs = williams_results.x
            a_n = self.williams_coeffs[:len(self.optimization.terms)]
            b_n = self.williams_coeffs[len(self.optimization.terms):]
            self.williams_fit_a_n = {n: a_n[index] for index, n in enumerate(self.optimization.terms)}
            self.williams_fit_b_n = {n: b_n[index] for index, n in enumerate(self.optimization.terms)}

            # derive stress intensity factors and T-stress [Kuna formula 3.45]
            K_I = np.sqrt(2 * np.pi) * self.williams_fit_a_n[1] / np.sqrt(1000)
            K_II = -np.sqrt(2 * np.pi) * self.williams_fit_b_n[1] / np.sqrt(1000)
            T = 4 * self.williams_fit_a_n[2]

            model_cls = _create_williams_model(self.optimization.terms)
            fields = {f'a_{n}': self.williams_fit_a_n[n] for n in self.optimization.terms}
            fields.update({f'b_{n}': self.williams_fit_b_n[n] for n in self.optimization.terms})
            self.sifs_fit = model_cls(
                error=williams_results.cost,
                K_I=K_I,
                K_II=K_II,
                K_V=np.nan,
                T=T,
                **fields,
            )

        except Exception:
            print('Williams optimization failed.')
            self.williams_fit_a_n = {n: np.nan for index, n in enumerate(self.optimization.terms)}
            self.williams_fit_b_n = {n: np.nan for index, n in enumerate(self.optimization.terms)}
            model_cls = _create_williams_model(self.optimization.terms)
            fields = {f'a_{n}': np.nan for n in self.optimization.terms}
            fields.update({f'b_{n}': np.nan for n in self.optimization.terms})
            self.sifs_fit = model_cls(
                error=np.nan,
                K_I=np.nan,
                K_II=np.nan,
                K_V=np.nan,
                T=np.nan,
                **fields,
            )

    def _run_line_integrals(self, progress='off', task_id=None) -> None:
        """Calculate line integrals and aggregate the results."""
        # calculate Williams coefficients with Bueckner-Chen integral method
        current_size_left = self.integral_properties.integral_size_left
        current_size_right = self.integral_properties.integral_size_right
        current_size_top = self.integral_properties.integral_size_top
        current_size_bottom = self.integral_properties.integral_size_bottom

        if progress is None:
            iterator = progress_rich.track(range(self.integral_properties.number_of_paths),
                                           description='Calculating integrals')
        else:
            iterator = range(self.integral_properties.number_of_paths)

        for n in iterator:
            # Calculate one integral
            line_integral, current_int_sizes = calculate_line_integral(
                self.data,
                self.material,
                self.integral_properties,
                current_size_left,
                current_size_right,
                current_size_bottom,
                current_size_top,
                self.integral_properties.mask_tolerance,
                self.integral_properties.buckner_williams_terms,
            )

            self.results.append([line_integral.j_integral,
                                 line_integral.sif_k_j,
                                 line_integral.sif_k_i,
                                 line_integral.sif_k_ii,
                                 line_integral.t_stress_chen,
                                 line_integral.t_stress_sdm,
                                 line_integral.t_stress_int])
            self.williams_int_a_n.append(line_integral.williams_a_n)
            self.williams_int_b_n.append(line_integral.williams_b_n)
            self.williams_int.append(line_integral.williams_coefficients)
            self.int_sizes.append(current_int_sizes)
            self.integration_points.append([list(line_integral.np_integration_points[:, 0]),
                                            list(line_integral.np_integration_points[:, 1])])
            self.num_of_path_nodes.append(line_integral.integration_path.path_properties.number_of_nodes)
            self.tick_sizes.append(line_integral.integration_path.path_properties.tick_size)

            # Update path
            current_size_left -= self.integral_properties.paths_distance_left
            current_size_right += self.integral_properties.paths_distance_right
            current_size_bottom -= self.integral_properties.paths_distance_bottom
            current_size_top += self.integral_properties.paths_distance_top

            # Update progress bar
            if progress != "off":
                progress[task_id] = {"progress": n + 1, "total": self.integral_properties.number_of_paths}

        self._aggregate_integral_results()

    def _aggregate_integral_results(self) -> None:
        """Aggregate statistics from the calculated line integrals."""
        # catch RuntimeWarnings originating from np.nanmean having no valid values
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)

            res_array = np.asarray(self.results)
            self.williams_int = np.asarray(self.williams_int)
            self.williams_int_a_n = np.asarray(self.williams_int_a_n)
            self.williams_int_b_n = np.asarray(self.williams_int_b_n)

            # Calculate means
            mean_j, mean_sif_j, mean_sif_k_i, mean_sif_k_ii, mean_t_stress_chen, mean_t_stress_sdm, mean_t_stress_int = \
                np.nanmean(res_array, axis=0)
            mean_williams_int_a_n = np.nanmean(self.williams_int_a_n, axis=0)
            mean_williams_int_b_n = np.nanmean(self.williams_int_b_n, axis=0)

            # Calculate medians
            med_j, med_sif_j, med_sif_k_i, med_sif_k_ii, med_t_stress_chen, med_t_stress_sdm, med_t_stress_int = \
                np.nanmedian(res_array, axis=0)
            med_williams_int_a_n = np.nanmedian(self.williams_int_a_n, axis=0)
            med_williams_int_b_n = np.nanmedian(self.williams_int_b_n, axis=0)

            # Calculate means rejecting outliers
            rej_out_mean_j, rej_out_mean_sif_j, rej_out_mean_sif_k_i, rej_out_mean_sif_k_ii, \
            rej_out_mean_t_stress_chen, rej_out_mean_t_stress_sdm, rej_out_mean_t_stress_int = \
                self.mean_wo_outliers(res_array, m=2)

            rej_out_mean_williams_int_a_n = self.mean_wo_outliers(self.williams_int_a_n, m=2)
            rej_out_mean_williams_int_b_n = self.mean_wo_outliers(self.williams_int_b_n, m=2)

        # calculate SIFs with Bueckner-Chen integral method
        term_index = self.integral_properties.buckner_williams_terms.index(1)
        mean_k_i_chen = np.sqrt(2 * np.pi) * mean_williams_int_a_n[term_index] / np.sqrt(1000)
        med_k_i_chen = np.sqrt(2 * np.pi) * med_williams_int_a_n[term_index] / np.sqrt(1000)
        rej_out_mean_k_i_chen = np.sqrt(2 * np.pi) * rej_out_mean_williams_int_a_n[term_index] / np.sqrt(1000)
        mean_k_ii_chen = -np.sqrt(2 * np.pi) * mean_williams_int_b_n[term_index] / np.sqrt(1000)
        med_k_ii_chen = -np.sqrt(2 * np.pi) * med_williams_int_b_n[term_index] / np.sqrt(1000)
        rej_out_mean_k_ii_chen = -np.sqrt(2 * np.pi) * rej_out_mean_williams_int_b_n[term_index] / np.sqrt(1000)

        # bundle means / medians / means using outlier rejection
        self.sifs_int = {
            'mean': SIFsIntegralMeanResults(
                J=mean_j,
                K_J=mean_sif_j,
                K_I_interac=mean_sif_k_i,
                K_II_interac=mean_sif_k_ii,
                K_I_Chen=mean_k_i_chen,
                K_II_Chen=mean_k_ii_chen,
                T_Chen=mean_t_stress_chen,
                T_SDM=mean_t_stress_sdm,
                T_interac=mean_t_stress_int,
            ),
            'median': SIFsIntegralMedianResults(
                J=med_j,
                K_J=med_sif_j,
                K_I_interac=med_sif_k_i,
                K_II_interac=med_sif_k_ii,
                K_I_Chen=med_k_i_chen,
                K_II_Chen=med_k_ii_chen,
                T_Chen=med_t_stress_chen,
                T_SDM=med_t_stress_sdm,
                T_interac=med_t_stress_int,
            ),
            'rej_out_mean': SIFsIntegralMeanwoOutlierResults(
                J=rej_out_mean_j,
                K_J=rej_out_mean_sif_j,
                K_I_interac=rej_out_mean_sif_k_i,
                K_II_interac=rej_out_mean_sif_k_ii,
                K_I_Chen=rej_out_mean_k_i_chen,
                K_II_Chen=rej_out_mean_k_ii_chen,
                T_Chen=rej_out_mean_t_stress_chen,
                T_SDM=rej_out_mean_t_stress_sdm,
                T_interac=rej_out_mean_t_stress_int,
            ),
            'williams_int_a_n': {
                'mean': mean_williams_int_a_n,
                'median': med_williams_int_a_n,
                'rej_out_mean': rej_out_mean_williams_int_a_n,
            },
            'williams_int_b_n': {
                'mean': mean_williams_int_b_n,
                'median': med_williams_int_b_n,
                'rej_out_mean': rej_out_mean_williams_int_b_n,
            },
        }

    @staticmethod
    def mean_wo_outliers(data: np.ndarray, m=2) -> list:
        mean_wo_outliers = []
        for data_i in data.T:
            d = np.abs(data_i - np.nanmedian(data_i))
            mdev = np.nanmedian(d)
            s = d / mdev if mdev else 0
            mean_wo_outliers.append(np.nanmean(data_i[s < m]))
        return mean_wo_outliers

