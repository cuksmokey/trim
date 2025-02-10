import numpy as np
from trimming_state import trimming_state


def check_interruption(substance_id):
    """Helper function to check if calculation should be interrupted"""
    try:
        if substance_id is not None:
            return (not trimming_state.is_processing(substance_id) or
                    trimming_state.is_periodic_update_running())
    except Exception as e:
        print(f"Warning: Could not check interruption state: {e}")
        return False
    return False

def arrays_equal(arr1, arr2):
    """Compare two numpy arrays for equality, handling None values"""
    if arr1 is None or arr2 is None:
        return arr1 is arr2
    return np.array_equal(arr1, arr2)

def trimming_random(order, ukuran, lebar_1, lebar_2, lebar_3, substance_id=None):
    """
        Modified trimming calculation with interrupt checks
        Returns (ukuran_finaltrim_sisaorder_final, weight_final, detail_trim_PM1_PM2, cut_1_final)
    """

    a = np.zeros((len(order), 6))
    weight_final = float('inf')
    weight_constant = 3 / 385
    orderan = order.copy()

    # Initialize trim_detail_final
    trim_detail_final = np.empty((0, 6))
    cut_1_final = 0
    ukuran_finaltrim_sisaorder_final = None

    # Variables for weight checkpoint optimization
    checkpoint_interval = 2000  # Check every 2000 iterations
    best_weights_history = []  # Store best weights for each checkpoint
    current_checkpoint_best = float('inf')

    # Variables for optimization checks
    last_five_results = []  # Store last 5 trim detail results
    best_results = {
        'weight': float('inf'),
        'details': None,
        'ukuran_final': None,
        'cut_1': 0
    }
    consecutive_same_results = 0
    last_detail = None

    for z in range(30000):
        # Check for interrupts
        if check_interruption(substance_id):
            print(f"Trimming calculation interrupted for substance {substance_id}")
            return None, None, None, None

        order = orderan.copy()
        trim = np.zeros(len(order))
        a = np.zeros((len(order), 6))
        trim_detail = np.empty((0, 6))  # Initialize with 12 columns
        x = 0
        cut_1 = 0

        # Trim Random PM1 (2 Out)
        for r in range(1000):
            randomizer_1 = np.random.randint(0, len(order))
            randomizer_2 = np.random.randint(0, len(order))
            if lebar_1 - 12 <= ukuran[randomizer_2] + ukuran[randomizer_1] <= lebar_1 and randomizer_1 != randomizer_2:
                substract = min(order[randomizer_2], order[randomizer_1])
                order[randomizer_2] -= substract
                order[randomizer_1] -= substract
                trim[randomizer_2] += substract
                trim[randomizer_1] += substract
                if substract != 0:
                    x += 1
                    trim_detail = np.vstack(
                        [trim_detail, [ukuran[randomizer_2], substract, ukuran[randomizer_1], substract,0,0]])
                cut_1 += substract
            elif lebar_1 - 12 <= ukuran[randomizer_2] + ukuran[
                randomizer_1] <= lebar_1 and randomizer_1 == randomizer_2:
                if order[randomizer_2] % 2 == 0:
                    substract = min(order[randomizer_2], order[randomizer_1])
                    order[randomizer_2] -= substract
                    trim[randomizer_2] += substract
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack(
                            [trim_detail, [ukuran[randomizer_2], substract / 2, ukuran[randomizer_2], substract / 2,0,0]])
                    cut_1 += substract / 2
                elif order[randomizer_2] % 2 == 1:
                    substract = min(order[randomizer_2], order[randomizer_1])
                    order[randomizer_2] -= (substract - 1)
                    trim[randomizer_2] += (substract - 1)
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_2], (substract - 1) / 2, ukuran[randomizer_2],
                                                  (substract - 1) / 2,0,0]])
                    cut_1 += (substract - 1) / 2

        # Trim Random PM1 (3 Out)
        for i in range(1000):
            if not trimming_state.is_processing(substance_id) or \
                    trimming_state.is_periodic_update_running():
                print(f"Trimming calculation interrupted for substance {substance_id}")
                return None, None, None, None

            randomizer_3 = np.random.randint(0, len(order))
            randomizer_4 = np.random.randint(0, len(order))
            randomizer_5 = np.random.randint(0, len(order))
            if (lebar_1 - 12 <= ukuran[randomizer_3] + ukuran[randomizer_4] + ukuran[randomizer_5] <= lebar_1 and
                    randomizer_3 != randomizer_4 and randomizer_3 != randomizer_5 and randomizer_5 != randomizer_4 and
                    order[randomizer_3] > 0 and order[randomizer_4] > 0 and order[randomizer_5] > 0):
                substract = min(order[randomizer_3], order[randomizer_4], order[randomizer_5])
                order[randomizer_3] -= substract
                order[randomizer_4] -= substract
                order[randomizer_5] -= substract
                trim[randomizer_3] += substract
                trim[randomizer_4] += substract
                trim[randomizer_5] += substract
                if substract != 0:
                    x += 1
                    trim_detail = np.vstack([trim_detail,
                                             [ukuran[randomizer_3], substract, ukuran[randomizer_4], substract,
                                              ukuran[randomizer_5], substract]])
                cut_1 += substract
            elif (lebar_1 - 12 <= ukuran[randomizer_3] + ukuran[randomizer_4] + ukuran[randomizer_5] <= lebar_1 and
                  randomizer_3 != randomizer_4 and randomizer_3 != randomizer_5 and randomizer_5 == randomizer_4 and
                  order[randomizer_3] > 0 and order[randomizer_4] > 0 and order[randomizer_5] > 0):
                if order[randomizer_5] / 2 >= order[randomizer_3]:
                    substract = min(order[randomizer_3], order[randomizer_5])
                    order[randomizer_5] -= substract * 2
                    trim[randomizer_5] += substract * 2
                    order[randomizer_3] -= substract
                    trim[randomizer_3] += substract
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract, ukuran[randomizer_4], substract,
                                                  ukuran[randomizer_5], substract]])
                    cut_1 += substract
                elif order[randomizer_5] / 2 < order[randomizer_3] <= order[randomizer_5] and order[
                    randomizer_5] % 2 == 0:
                    substract = max(order[randomizer_3], order[randomizer_5])
                    order[randomizer_5] -= substract
                    trim[randomizer_5] += substract
                    order[randomizer_3] -= substract / 2
                    trim[randomizer_3] += substract / 2
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract / 2, ukuran[randomizer_4],
                                                  substract / 2, ukuran[randomizer_5], substract / 2]])
                    cut_1 += substract / 2
                elif order[randomizer_5] / 2 < order[randomizer_3] <= order[randomizer_5] and order[
                    randomizer_5] % 2 == 1:
                    substract = max(order[randomizer_3], order[randomizer_5])
                    order[randomizer_5] -= (substract - 1)
                    trim[randomizer_5] += (substract - 1)
                    order[randomizer_3] -= (substract - 1) / 2
                    trim[randomizer_3] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 1) / 2, ukuran[randomizer_4],
                                                  (substract - 1) / 2, ukuran[randomizer_5], (substract - 1) / 2]])
                    cut_1 += (substract - 1) / 2
                elif order[randomizer_5] < order[randomizer_3] and order[randomizer_5] % 2 == 0:
                    substract = min(order[randomizer_3], order[randomizer_5])
                    order[randomizer_5] -= substract
                    trim[randomizer_5] += substract
                    order[randomizer_3] -= substract / 2
                    trim[randomizer_3] += substract / 2
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract / 2, ukuran[randomizer_4],
                                                  substract / 2, ukuran[randomizer_5], substract / 2]])
                    cut_1 += substract / 2
                elif order[randomizer_5] < order[randomizer_3] and order[randomizer_5] % 2 == 1:
                    substract = min(order[randomizer_3], order[randomizer_5])
                    order[randomizer_5] -= (substract - 1)
                    trim[randomizer_5] += (substract - 1)
                    order[randomizer_3] -= (substract - 1) / 2
                    trim[randomizer_3] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 1) / 2, ukuran[randomizer_4],
                                                  (substract - 1) / 2, ukuran[randomizer_5], (substract - 1) / 2]])
                    cut_1 += (substract - 1) / 2
            elif (lebar_1 - 12 <= ukuran[randomizer_3] + ukuran[randomizer_4] + ukuran[randomizer_5] <= lebar_1 and
                  randomizer_3 != randomizer_4 and randomizer_3 == randomizer_5 and randomizer_5 != randomizer_4 and
                  order[randomizer_3] > 0 and order[randomizer_4] > 0 and order[randomizer_5] > 0):
                if order[randomizer_3] / 2 >= order[randomizer_4]:
                    substract = min(order[randomizer_3], order[randomizer_4])
                    order[randomizer_3] -= substract * 2
                    trim[randomizer_3] += substract * 2
                    order[randomizer_4] -= substract
                    trim[randomizer_4] += substract
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract, ukuran[randomizer_4], substract,
                                                  ukuran[randomizer_5], substract]])
                    cut_1 += substract
                elif order[randomizer_3] / 2 < order[randomizer_4] <= order[randomizer_3] and order[
                    randomizer_3] % 2 == 0:
                    substract = max(order[randomizer_3], order[randomizer_4])
                    order[randomizer_3] -= substract
                    trim[randomizer_3] += substract
                    order[randomizer_4] -= substract / 2
                    trim[randomizer_4] += substract / 2
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract / 2, ukuran[randomizer_4],
                                                  substract / 2, ukuran[randomizer_5], substract / 2]])
                    cut_1 += substract / 2
                elif order[randomizer_3] / 2 < order[randomizer_4] <= order[randomizer_3] and order[
                    randomizer_3] % 2 == 1:
                    substract = max(order[randomizer_3], order[randomizer_4])
                    order[randomizer_3] -= (substract - 1)
                    trim[randomizer_3] += (substract - 1)
                    order[randomizer_4] -= (substract - 1) / 2
                    trim[randomizer_4] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 1) / 2, ukuran[randomizer_4],
                                                  (substract - 1) / 2, ukuran[randomizer_5], (substract - 1) / 2]])
                    cut_1 += (substract - 1) / 2
                elif order[randomizer_3] < order[randomizer_4] and order[randomizer_3] % 2 == 0:
                    substract = min(order[randomizer_3], order[randomizer_4])
                    order[randomizer_3] -= substract
                    trim[randomizer_3] += substract
                    order[randomizer_4] -= substract / 2
                    trim[randomizer_4] += substract / 2
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract / 2, ukuran[randomizer_4],
                                                  substract / 2, ukuran[randomizer_5], substract / 2]])
                    cut_1 += substract / 2
                elif order[randomizer_3] < order[randomizer_4] and order[randomizer_3] % 2 == 1:
                    substract = min(order[randomizer_3], order[randomizer_4])
                    order[randomizer_3] -= (substract - 1)
                    trim[randomizer_3] += (substract - 1)
                    order[randomizer_4] -= (substract - 1) / 2
                    trim[randomizer_4] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 1) / 2, ukuran[randomizer_4],
                                                  (substract - 1) / 2, ukuran[randomizer_5], (substract - 1) / 2]])
                    cut_1 += (substract - 1) / 2
            elif (lebar_1 - 12 <= ukuran[randomizer_3] + ukuran[randomizer_4] + ukuran[randomizer_5] <= lebar_1 and
                  randomizer_3 == randomizer_4 and randomizer_3 != randomizer_5 and randomizer_5 != randomizer_4 and
                  order[randomizer_3] > 0 and order[randomizer_4] > 0 and order[randomizer_5] > 0):
                if order[randomizer_3] / 2 >= order[randomizer_5]:
                    substract = min(order[randomizer_3], order[randomizer_5])
                    order[randomizer_3] -= substract * 2
                    trim[randomizer_3] += substract * 2
                    order[randomizer_5] -= substract
                    trim[randomizer_5] += substract
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract, ukuran[randomizer_4], substract,
                                                  ukuran[randomizer_5], substract]])
                    cut_1 += substract
                elif order[randomizer_3] / 2 < order[randomizer_5] <= order[randomizer_3] and order[
                    randomizer_3] % 2 == 0:
                    substract = max(order[randomizer_3], order[randomizer_5])
                    order[randomizer_3] -= substract
                    trim[randomizer_3] += substract
                    order[randomizer_5] -= substract / 2
                    trim[randomizer_5] += substract / 2
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract / 2, ukuran[randomizer_4],
                                                  substract / 2, ukuran[randomizer_5], substract / 2]])
                    cut_1 += substract / 2
                elif order[randomizer_3] / 2 < order[randomizer_5] <= order[randomizer_3] and order[
                    randomizer_3] % 2 == 1:
                    substract = max(order[randomizer_3], order[randomizer_5])
                    order[randomizer_3] -= (substract - 1)
                    trim[randomizer_3] += (substract - 1)
                    order[randomizer_5] -= (substract - 1) / 2
                    trim[randomizer_5] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 1) / 2, ukuran[randomizer_4],
                                                  (substract - 1) / 2, ukuran[randomizer_5], (substract - 1) / 2]])
                    cut_1 += (substract - 1) / 2
                elif order[randomizer_3] < order[randomizer_5] and order[randomizer_3] % 2 == 0:
                    substract = min(order[randomizer_3], order[randomizer_5])
                    order[randomizer_3] -= substract
                    trim[randomizer_3] += substract
                    order[randomizer_5] -= substract / 2
                    trim[randomizer_5] += substract / 2
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract / 2, ukuran[randomizer_4],
                                                  substract / 2, ukuran[randomizer_5], substract / 2]])
                    cut_1 += substract / 2
                elif order[randomizer_3] < order[randomizer_5] and order[randomizer_3] % 2 == 1:
                    substract = min(order[randomizer_3], order[randomizer_5])
                    order[randomizer_3] -= (substract - 1)
                    trim[randomizer_3] += (substract - 1)
                    order[randomizer_5] -= (substract - 1) / 2
                    trim[randomizer_5] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 1) / 2, ukuran[randomizer_4],
                                                  (substract - 1) / 2, ukuran[randomizer_5], (substract - 1) / 2]])
                    cut_1 += (substract - 1) / 2
            elif (lebar_1 - 12 <= ukuran[randomizer_3] + ukuran[randomizer_4] + ukuran[randomizer_5] <= lebar_1 and
                  randomizer_3 == randomizer_4 and randomizer_3 == randomizer_5 and randomizer_5 == randomizer_4 and
                  order[randomizer_3] > 0 and order[randomizer_4] > 0 and order[randomizer_5] > 0):
                if order[randomizer_3] % 3 == 0:
                    substract = min(order[randomizer_3], order[randomizer_4], order[randomizer_5])
                    order[randomizer_3] -= substract
                    trim[randomizer_3] += substract
                    if substract != 0:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], substract / 3, ukuran[randomizer_4],
                                                  substract / 3, ukuran[randomizer_5], substract / 3]])
                    cut_1 += substract / 3
                elif order[randomizer_3] % 3 == 1:
                    substract = min(order[randomizer_3], order[randomizer_4], order[randomizer_5])
                    order[randomizer_3] -= (substract - 1)
                    trim[randomizer_3] += (substract - 1)
                    if substract != 0 and substract != 1:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 1) / 3, ukuran[randomizer_4],
                                                  (substract - 1) / 3, ukuran[randomizer_5], (substract - 1) / 3]])
                    cut_1 += (substract - 1) / 3
                elif order[randomizer_3] % 3 == 2:
                    substract = min(order[randomizer_3], order[randomizer_4], order[randomizer_5])
                    order[randomizer_3] -= (substract - 2)
                    trim[randomizer_3] += (substract - 2)
                    if substract != 0 and substract != 2:
                        x += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_3], (substract - 2) / 3, ukuran[randomizer_4],
                                                  (substract - 2) / 3, ukuran[randomizer_5], (substract - 2) / 3]])
                    cut_1 += (substract - 2) / 3

        a[:, 0] = ukuran
        a[:, 1] = trim
        a[:, 2] = order

        # Variables for Trim in PM2 (After Trim in PM1)
        order_2 = order.copy()
        trim_2 = trim.copy()
        x_2 = 0
        cut_2 = 0

        # Trim Random PM2 (2 Out)
        for y in range(1000):
            if not trimming_state.is_processing(substance_id) or \
                    trimming_state.is_periodic_update_running():
                print(f"Trimming calculation interrupted for substance {substance_id}")
                return None, None, None, None

            randomizer_6 = np.random.randint(0, len(order_2))
            randomizer_7 = np.random.randint(0, len(order_2))
            if lebar_2 - 12 <= ukuran[randomizer_7] + ukuran[randomizer_6] <= lebar_2 and randomizer_6 != randomizer_7:
                substract = min(order_2[randomizer_7], order_2[randomizer_6])
                order_2[randomizer_7] -= substract
                order_2[randomizer_6] -= substract
                trim_2[randomizer_7] += substract
                trim_2[randomizer_6] += substract
                if substract != 0:
                    x_2 += 1
                    trim_detail = np.vstack([trim_detail,
                                             [ukuran[randomizer_7], substract, ukuran[randomizer_6],
                                              substract, 0, 0]])
                cut_2 += substract
            elif lebar_2 - 12 <= ukuran[randomizer_7] + ukuran[
                randomizer_6] <= lebar_2 and randomizer_6 == randomizer_7:
                if order_2[randomizer_7] % 2 == 0:
                    substract = order_2[randomizer_7]
                    order_2[randomizer_7] -= substract
                    trim_2[randomizer_7] += substract
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail, [ukuran[randomizer_7], substract / 2,
                                                               ukuran[randomizer_7], substract / 2, 0, 0]])
                    cut_2 += substract / 2
                elif order_2[randomizer_7] % 2 == 1:
                    substract = order_2[randomizer_7]
                    order_2[randomizer_7] -= (substract - 1)
                    trim_2[randomizer_7] += (substract - 1)
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_7], (substract - 1) / 2,
                                                  ukuran[randomizer_7], (substract - 1) / 2, 0, 0]])
                    cut_2 += (substract - 1) / 2

        # Trim Random PM2 (3 Out)
        for k in range(1000):
            if not trimming_state.is_processing(substance_id) or \
                    trimming_state.is_periodic_update_running():
                print(f"Trimming calculation interrupted for substance {substance_id}")
                return None, None, None, None

            randomizer_8 = np.random.randint(0, len(order_2))
            randomizer_9 = np.random.randint(0, len(order_2))
            randomizer_10 = np.random.randint(0, len(order_2))
            if (lebar_3 - 12 <= ukuran[randomizer_8] + ukuran[randomizer_9] + ukuran[randomizer_10] <= lebar_3 and
                    randomizer_8 != randomizer_9 and randomizer_8 != randomizer_10 and randomizer_10 != randomizer_9 and
                    order_2[randomizer_8] > 0 and order_2[randomizer_9] > 0 and order_2[randomizer_10] > 0):
                substract = min(order_2[randomizer_8], order_2[randomizer_9], order_2[randomizer_10])
                order_2[randomizer_8] -= substract
                order_2[randomizer_9] -= substract
                order_2[randomizer_10] -= substract
                trim_2[randomizer_8] += substract
                trim_2[randomizer_9] += substract
                trim_2[randomizer_10] += substract
                if substract != 0:
                    x_2 += 1
                    trim_detail = np.vstack([trim_detail,
                                             [ukuran[randomizer_8], substract, ukuran[randomizer_9], substract,
                                              ukuran[randomizer_10], substract]])
                cut_2 += substract
            elif (lebar_3 - 12 <= ukuran[randomizer_8] + ukuran[randomizer_9] + ukuran[randomizer_10] <= lebar_3 and
                  randomizer_8 != randomizer_9 and randomizer_8 != randomizer_10 and randomizer_10 == randomizer_9 and
                  order_2[randomizer_8] > 0 and order_2[randomizer_9] > 0 and order_2[randomizer_10] > 0):
                if order_2[randomizer_10] / 2 >= order_2[randomizer_8]:
                    substract = min(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_10] -= substract * 2
                    trim_2[randomizer_10] += substract * 2
                    order_2[randomizer_8] -= substract
                    trim_2[randomizer_8] += substract
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract, ukuran[randomizer_9], substract,
                                                  ukuran[randomizer_10], substract]])
                    cut_2 += substract
                elif order_2[randomizer_10] / 2 < order_2[randomizer_8] <= order_2[randomizer_10] and order_2[
                    randomizer_10] % 2 == 0:
                    substract = max(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_10] -= substract
                    trim_2[randomizer_10] += substract
                    order_2[randomizer_8] -= substract / 2
                    trim_2[randomizer_8] += substract / 2
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract / 2, ukuran[randomizer_9],
                                                  substract / 2, ukuran[randomizer_10], substract / 2]])
                    cut_2 += substract / 2
                elif order_2[randomizer_10] / 2 < order_2[randomizer_8] <= order_2[randomizer_10] and order_2[
                    randomizer_10] % 2 == 1:
                    substract = max(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_10] -= (substract - 1)
                    trim_2[randomizer_10] += (substract - 1)
                    order_2[randomizer_8] -= (substract - 1) / 2
                    trim_2[randomizer_8] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 1) / 2, ukuran[randomizer_9],
                                                  (substract - 1) / 2, ukuran[randomizer_10], (substract - 1) / 2]])
                    cut_2 += (substract - 1) / 2
                elif order_2[randomizer_10] < order_2[randomizer_8] and order_2[randomizer_10] % 2 == 0:
                    substract = min(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_10] -= substract
                    trim_2[randomizer_10] += substract
                    order_2[randomizer_8] -= substract / 2
                    trim_2[randomizer_8] += substract / 2
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract / 2, ukuran[randomizer_9],
                                                  substract / 2, ukuran[randomizer_10], substract / 2]])
                    cut_2 += substract / 2
                elif order_2[randomizer_10] < order_2[randomizer_8] and order_2[randomizer_10] % 2 == 1:
                    substract = min(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_10] -= (substract - 1)
                    trim_2[randomizer_10] += (substract - 1)
                    order_2[randomizer_8] -= (substract - 1) / 2
                    trim_2[randomizer_8] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 1) / 2, ukuran[randomizer_9],
                                                  (substract - 1) / 2, ukuran[randomizer_10], (substract - 1) / 2]])
                    cut_2 += (substract - 1) / 2
            elif (lebar_3 - 12 <= ukuran[randomizer_8] + ukuran[randomizer_9] + ukuran[randomizer_10] <= lebar_3 and
                  randomizer_8 != randomizer_9 and randomizer_8 == randomizer_10 and randomizer_10 != randomizer_9 and
                  order_2[randomizer_8] > 0 and order_2[randomizer_9] > 0 and order_2[randomizer_10] > 0):
                if order_2[randomizer_8] / 2 >= order_2[randomizer_9]:
                    substract = min(order_2[randomizer_8], order_2[randomizer_9])
                    order_2[randomizer_8] -= substract * 2
                    trim_2[randomizer_8] += substract * 2
                    order_2[randomizer_9] -= substract
                    trim_2[randomizer_9] += substract
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract, ukuran[randomizer_9], substract,
                                                  ukuran[randomizer_10], substract]])
                    cut_2 += substract
                elif order_2[randomizer_8] / 2 < order_2[randomizer_9] <= order_2[randomizer_8] and order_2[
                    randomizer_8] % 2 == 0:
                    substract = max(order_2[randomizer_8], order_2[randomizer_9])
                    order_2[randomizer_8] -= substract
                    trim_2[randomizer_8] += substract
                    order_2[randomizer_9] -= substract / 2
                    trim_2[randomizer_9] += substract / 2
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract / 2, ukuran[randomizer_9],
                                                  substract / 2, ukuran[randomizer_10], substract / 2]])
                    cut_2 += substract / 2
                elif order_2[randomizer_8] / 2 < order_2[randomizer_9] <= order_2[randomizer_8] and order_2[
                    randomizer_8] % 2 == 1:
                    substract = max(order_2[randomizer_8], order_2[randomizer_9])
                    order_2[randomizer_8] -= (substract - 1)
                    trim_2[randomizer_8] += (substract - 1)
                    order_2[randomizer_9] -= (substract - 1) / 2
                    trim_2[randomizer_9] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 1) / 2, ukuran[randomizer_9],
                                                  (substract - 1) / 2, ukuran[randomizer_10], (substract - 1) / 2]])
                    cut_2 += (substract - 1) / 2
                elif order_2[randomizer_8] < order_2[randomizer_9] and order_2[randomizer_8] % 2 == 0:
                    substract = min(order_2[randomizer_8], order_2[randomizer_9])
                    order_2[randomizer_8] -= substract
                    trim_2[randomizer_8] += substract
                    order_2[randomizer_9] -= substract / 2
                    trim_2[randomizer_9] += substract / 2
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract / 2, ukuran[randomizer_9],
                                                  substract / 2, ukuran[randomizer_10], substract / 2]])
                    cut_2 += substract / 2
                elif order_2[randomizer_8] < order_2[randomizer_9] and order_2[randomizer_8] % 2 == 1:
                    substract = min(order_2[randomizer_8], order_2[randomizer_9])
                    order_2[randomizer_8] -= (substract - 1)
                    trim_2[randomizer_8] += (substract - 1)
                    order_2[randomizer_9] -= (substract - 1) / 2
                    trim_2[randomizer_9] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 1) / 2, ukuran[randomizer_9],
                                                  (substract - 1) / 2, ukuran[randomizer_10], (substract - 1) / 2]])
                    cut_2 += (substract - 1) / 2
            elif (lebar_3 - 12 <= ukuran[randomizer_8] + ukuran[randomizer_9] + ukuran[randomizer_10] <= lebar_3 and
                  randomizer_8 == randomizer_9 and randomizer_8 != randomizer_10 and randomizer_10 != randomizer_9 and
                  order_2[randomizer_8] > 0 and order_2[randomizer_9] > 0 and order_2[randomizer_10] > 0):
                if order_2[randomizer_8] / 2 >= order_2[randomizer_10]:
                    substract = min(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_8] -= substract * 2
                    trim_2[randomizer_8] += substract * 2
                    order_2[randomizer_10] -= substract
                    trim_2[randomizer_10] += substract
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract, ukuran[randomizer_9], substract,
                                                  ukuran[randomizer_10], substract]])
                    cut_2 += substract
                elif order_2[randomizer_8] / 2 < order_2[randomizer_10] <= order_2[randomizer_8] and order_2[
                    randomizer_8] % 2 == 0:
                    substract = max(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_8] -= substract
                    trim_2[randomizer_8] += substract
                    order_2[randomizer_10] -= substract / 2
                    trim_2[randomizer_10] += substract / 2
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract / 2, ukuran[randomizer_9],
                                                  substract / 2, ukuran[randomizer_10], substract / 2]])
                    cut_2 += substract / 2
                elif order_2[randomizer_8] / 2 < order_2[randomizer_10] <= order_2[randomizer_8] and order_2[
                    randomizer_8] % 2 == 1:
                    substract = max(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_8] -= (substract - 1)
                    trim_2[randomizer_8] += (substract - 1)
                    order_2[randomizer_10] -= (substract - 1) / 2
                    trim_2[randomizer_10] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 1) / 2, ukuran[randomizer_9],
                                                  (substract - 1) / 2, ukuran[randomizer_10], (substract - 1) / 2]])
                    cut_2 += (substract - 1) / 2
                elif order_2[randomizer_8] < order_2[randomizer_10] and order_2[randomizer_8] % 2 == 0:
                    substract = min(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_8] -= substract
                    trim_2[randomizer_8] += substract
                    order_2[randomizer_10] -= substract / 2
                    trim_2[randomizer_10] += substract / 2
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract / 2, ukuran[randomizer_9],
                                                  substract / 2, ukuran[randomizer_10], substract / 2]])
                    cut_2 += substract / 2
                elif order_2[randomizer_8] < order_2[randomizer_10] and order_2[randomizer_8] % 2 == 1:
                    substract = min(order_2[randomizer_8], order_2[randomizer_10])
                    order_2[randomizer_8] -= (substract - 1)
                    trim_2[randomizer_8] += (substract - 1)
                    order_2[randomizer_10] -= (substract - 1) / 2
                    trim_2[randomizer_10] += (substract - 1) / 2
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 1) / 2, ukuran[randomizer_9],
                                                  (substract - 1) / 2, ukuran[randomizer_10], (substract - 1) / 2]])
                    cut_2 += (substract - 1) / 2
            elif (lebar_3 - 12 <= ukuran[randomizer_8] + ukuran[randomizer_9] + ukuran[randomizer_10] <= lebar_3 and
                  randomizer_8 == randomizer_9 and randomizer_8 == randomizer_10 and randomizer_10 == randomizer_9 and
                  order_2[randomizer_8] > 0 and order_2[randomizer_9] > 0 and order_2[randomizer_10] > 0):
                if order_2[randomizer_8] % 3 == 0:
                    substract = min(order_2[randomizer_8], order_2[randomizer_9], order_2[randomizer_10])
                    order_2[randomizer_8] -= substract
                    trim_2[randomizer_8] += substract
                    if substract != 0:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], substract / 3, ukuran[randomizer_9],
                                                  substract / 3, ukuran[randomizer_10], substract / 3]])
                    cut_2 += substract / 3
                elif order_2[randomizer_8] % 3 == 1:
                    substract = min(order_2[randomizer_8], order_2[randomizer_9], order_2[randomizer_10])
                    order_2[randomizer_8] -= (substract - 1)
                    trim_2[randomizer_8] += (substract - 1)
                    if substract != 0 and substract != 1:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 1) / 3, ukuran[randomizer_9],
                                                  (substract - 1) / 3, ukuran[randomizer_10], (substract - 1) / 3]])
                    cut_2 += (substract - 1) / 3
                elif order_2[randomizer_8] % 3 == 2:
                    substract = min(order_2[randomizer_8], order_2[randomizer_9], order_2[randomizer_10])
                    order_2[randomizer_8] -= (substract - 2)
                    trim_2[randomizer_8] += (substract - 2)
                    if substract != 0 and substract != 2:
                        x_2 += 1
                        trim_detail = np.vstack([trim_detail,
                                                 [ukuran[randomizer_8], (substract - 2) / 3, ukuran[randomizer_9],
                                                  (substract - 2) / 3, ukuran[randomizer_10], (substract - 2) / 3]])
                    cut_2 += (substract - 2) / 3

        a[:, 3] = ukuran
        a[:, 4] = trim_2
        a[:, 5] = order_2

        ukuran_finaltrim_sisaorder = a

        weight = np.sum(ukuran * order_2) * weight_constant

        # Early stopping condition 1: Check if all orders are processed
        if np.all(order_2 == 0):
            print(f"Early stop: All orders processed at iteration {z}")
            return ukuran_finaltrim_sisaorder, weight, trim_detail, cut_1

        # Store result if it's better than previous best
        if weight < best_results['weight']:
            best_results['weight'] = weight
            best_results['details'] = trim_detail.copy()
            best_results['ukuran_final'] = ukuran_finaltrim_sisaorder.copy()
            best_results['cut_1'] = cut_1
            consecutive_same_results = 0  # Reset counter when we find a better result
        elif weight == best_results['weight']:
            # Check if the trim details are the same
            if arrays_equal(trim_detail, last_detail):
                consecutive_same_results += 1
                if consecutive_same_results >= 5:
                    print(f"Early stop: 5 consecutive same results at iteration {z}")
                    return (best_results['ukuran_final'],
                            best_results['weight'],
                            best_results['details'],
                            best_results['cut_1'])
            else:
                consecutive_same_results = 1

        last_detail = trim_detail.copy()

        # Update best weight for current checkpoint
        if weight < current_checkpoint_best:
            current_checkpoint_best = weight

        # Checkpoint logic
        if (z + 1) % checkpoint_interval == 0:
            print(f"Checkpoint at iteration {z + 1}: Best weight = {current_checkpoint_best}")
            best_weights_history.append(current_checkpoint_best)

            # Check if we have at least 3 checkpoints
            if len(best_weights_history) >= 3:
                # Check if any previous best weight matches current best weight within tolerance
                matches = any(abs(w - current_checkpoint_best) < 0.0001 for w in best_weights_history[:-1])
                if matches:
                    print(
                        f"Early stop: Found matching best weight (within tolerance) {current_checkpoint_best} in previous checkpoints")
                    print(f"Weight history: {best_weights_history}")
                    break

            # Reset for next checkpoint
            current_checkpoint_best = float('inf')

        # Update global best if needed
        if weight < weight_final:
            weight_final = weight
            ukuran_finaltrim_sisaorder_final = ukuran_finaltrim_sisaorder.copy()
            trim_detail_final = trim_detail.copy()
            cut_1_final = 0
        elif weight_final == weight and cut_1 > cut_1_final:
            cut_1_final = cut_1
            ukuran_finaltrim_sisaorder_final = ukuran_finaltrim_sisaorder.copy()
            trim_detail_final = trim_detail.copy()

        # Keep track of last 5 results
        last_five_results.append(trim_detail.copy())
        if len(last_five_results) > 5:
            last_five_results.pop(0)

    # At the end of your trimming_random function, modify this part:

    if len(trim_detail_final) > 0:
        # Remove zero rows (if any still exist)
        trim_detail_final = trim_detail_final[~np.all(trim_detail_final == 0, axis=1)]
    detail_trim_PM1_PM2 = trim_detail_final

    return ukuran_finaltrim_sisaorder_final, weight_final, detail_trim_PM1_PM2, cut_1_final