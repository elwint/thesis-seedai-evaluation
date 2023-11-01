import statsmodels.api as sm
import numpy as np

def two_proportion_ztest(count_success_group1, nobs_group1, count_success_group2, nobs_group2):
    """
    Conduct a two-proportion z-test
    
    Parameters:
    count_success_group1 : int
        the number of successes in group 1
    nobs_group1 : int
        the number of observations in group 1
    count_success_group2 : int
        the number of successes in group 2
    nobs_group2 : int
        the number of observations in group 2
    
    Returns:
    z_score : float
        z-score of the test
    p_value : float
        p-value of the test
    """
    
    # Creating a 2x2 contingency table
    count = np.array([count_success_group1, count_success_group2])
    nobs = np.array([nobs_group1, nobs_group2])
    
    z_score, p_value = sm.stats.proportions_ztest(count, nobs, alternative='two-sided')
    
    return z_score, p_value

# # # Example usage:
# count_success_group1 = 2
# nobs_group1 = 84
# count_success_group2 = 8
# nobs_group2 = 84

# z_score, p_value = two_proportion_ztest(count_success_group1, nobs_group1, count_success_group2, nobs_group2)

# print(f"Z-score: {z_score:.2f}")
# print(f"P-value: {p_value:.4f}")
