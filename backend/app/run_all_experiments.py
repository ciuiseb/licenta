import os
import json
import numpy as np
import matplotlib.pyplot as plt
import sympy
import torch

# ==============================================================================
# ATENTIE: Ajusteaza aceste importuri conform structurii folderelor tale!
# ==============================================================================
from app.services.pinn_service import PinnService
from app.services.symbolic import SymbolicSolver
from app.services.numerical import NumericalSolver

def run_tolerance_experiments():
    # Cream folderul pentru output
    os.makedirs("rezultate_licenta", exist_ok=True)

    # ==============================================================================
    # SETARI EXPERIMENTALE
    # ==============================================================================
    NUM_RUNS = 10 # Numarul de teste independente per configuratie (pentru medie)
    tolerances = [1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8]
    # tolerances = [1e-8]

    # Paleta de culori profesionala pentru grafice (viridis)
    colors = plt.cm.viridis(np.linspace(0, 1, len(tolerances)))

    # Definirea cazurilor de testare mixte (IVP și BVP)
    experiments = {
        # ======================================================================
        # CAZURI IVP (PROBLEME CAUCHY - Condiții evaluate într-un singur punct t=0)
        # ======================================================================
        # "IVP_1_Exponentiala": {
        #     "title": "IVP 1: Scădere Exponențială (Ordin 1, Liniară)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p: y_p + y,
        #     "conditions": [{'t': 0.0, 'val': 1.0, 'order': 0}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 1) + y_sym,
        #     "t_max": 5.0
        # },
        # "IVP_2_Logistica": {
        #     "title": "IVP 2: Model Logistic (Ordin 1, Neliniară)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p: y_p - y * (1.0 - y),
        #     "conditions": [{'t': 0.0, 'val': 0.5, 'order': 0}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 1) - y_sym * (1 - y_sym),
        #     "t_max": 10.0
        # },
        # "IVP_3_Bernoulli": {
        #     "title": "IVP 3: Ecuația Bernoulli (n=3, Neliniară)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p: y_p + y - y**3,
        #     "conditions": [{'t': 0.0, 'val': 0.5, 'order': 0}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 1) + y_sym - y_sym**3,
        #     "t_max": 5.0
        # },
        # "IVP_4_Riccati": {
        #     "title": "IVP 4: Ecuația Riccati (Neliniară, dependentă de timp)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p: y_p - (1.0 + t**2 - 2.0*t*y + y**2),
        #     "conditions": [{'t': 0.0, 'val': 0.0, 'order': 0}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 1) - (1 + t_sym**2 - 2*t_sym*y_sym + y_sym**2),
        #     "t_max": 3.0
        # },
        # "IVP_5_Oscilator": {
        #     "title": "IVP 5: Oscilator Armonic (Ordin 2, Liniară)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p, y_dp: y_dp + y,
        #     "conditions": [{'t': 0.0, 'val': 1.0, 'order': 0}, {'t': 0.0, 'val': 0.0, 'order': 1}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 2) + y_sym,
        #     "t_max": 10.0
        # },
        # "IVP_6_Pendul": {
        #     "title": "IVP 6: Pendul Matematic (Ordin 2, Neliniară)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p, y_dp: y_dp + torch.sin(y),
        #     "conditions": [{'t': 0.0, 'val': 0.785398, 'order': 0}, {'t': 0.0, 'val': 0.0, 'order': 1}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 2) + sympy.sin(y_sym),
        #     "t_max": 10.0
        # },
        # "IVP_7_Ordin_3_Liniar": {
        #     "title": "IVP 7: Ordin 3 Liniară (y''' + y' = 0)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p, y_dp, y_tp: y_tp + y_p,
        #     "conditions": [{'t': 0.0, 'val': 0.0, 'order': 0}, {'t': 0.0, 'val': 1.0, 'order': 1}, {'t': 0.0, 'val': 0.0, 'order': 2}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 3) + y_sym.diff(t_sym, 1),
        #     "t_max": 10.0
        # },
        # "IVP_8_Blasius": {
        #     "title": "IVP 8: Ecuația Blasius (Ordin 3, Neliniară)",
        #     "problem_type": "ivp",
        #     "physics": lambda t, y, y_p, y_dp, y_tp: y_tp + y * y_dp,
        #     "conditions": [{'t': 0.0, 'val': 0.0, 'order': 0}, {'t': 0.0, 'val': 0.0, 'order': 1}, {'t': 0.0, 'val': 1.0, 'order': 2}],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 3) + y_sym * y_sym.diff(t_sym, 2),
        #     "t_max": 5.0
        # },

        # ======================================================================
        # CAZURI BVP (VALORI PE FRONTIERĂ - Condiții distribuite în domeniu)
        # Notă: Ordinul 1 e exclus deoarece admite o singură condiție (deci e IVP).
        # ======================================================================
        # "BVP_1_Oscilator": {
        #     "title": "BVP 1: Oscilator Armonic (Ordin 2, Liniară)",
        #     "problem_type": "bvp",
        #     "physics": lambda t, y, y_p, y_dp: y_dp + y,
        #     "conditions": [
        #         {'t': 0.0, 'val': 1.0, 'order': 0},
        #         {'t': 1.57079, 'val': -1.0, 'order': 0}
        #     ],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 2) + y_sym,
        #     "t_max": 6.28
        # },
        "BVP_2_Pendul": {
            "title": "BVP 2: Pendul Matematic (Ordin 2, Neliniară)",
            "problem_type": "bvp",
            "physics": lambda t, y, y_p, y_dp: y_dp + torch.sin(y),
            "conditions": [
                {'t': 0.0, 'val': 1.0, 'order': 0},
                {'t': 2.0, 'val': 0.0, 'order': 0}
            ],
            "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 2) + sympy.sin(y_sym),
            "t_max": 2.0
        }
        # "BVP_3_Ordin_3_Liniar": {
        #     "title": "BVP 3: Ordin 3 Liniară (y''' + y' = 0)",
        #     "problem_type": "bvp",
        #     "physics": lambda t, y, y_p, y_dp, y_tp: y_tp + y_p,
        #     "conditions": [
        #         {'t': 0.0, 'val': 0.0, 'order': 0},
        #         {'t': 0.0, 'val': 1.0, 'order': 1},
        #         {'t': 3.14159, 'val': 0.0, 'order': 0}
        #     ],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 3) + y_sym.diff(t_sym, 1),
        #     "t_max": 6.28
        # },
        # "BVP_4_Blasius": {
        #     "title": "BVP 4: Ec. Blasius (Ordin 3, Neliniară)",
        #     "problem_type": "bvp",
        #     "physics": lambda t, y, y_p, y_dp, y_tp: y_tp + y * y_dp,
        #     "conditions": [
        #         {'t': 0.0, 'val': 0.0, 'order': 0},       # y(0) = 0
        #         {'t': 0.0, 'val': 0.0, 'order': 1},       # y'(0) = 0
        #         {'t': 5.0, 'val': 1.0, 'order': 1}        # y'(5) = 1 (Aproximare la asimptota spre infinit)
        #     ],
        #     "sympy_expr": lambda y_sym, t_sym: y_sym.diff(t_sym, 3) + y_sym * y_sym.diff(t_sym, 2),
        #     "t_max": 5.0
        # }
    }

    all_results = {}

    for case_id, exp in experiments.items():
        print(f"\n{'='*80}\nIncepem {case_id} ({NUM_RUNS} rulari independente / toleranta)\n{'='*80}")
        all_results[case_id] = {}

        # ==============================================================================
        # A. OBTINEREA SOLUTIEI DE REFERINTA (GROUND TRUTH)
        # ==============================================================================
        t_sym = sympy.Symbol('t')
        y_sym = sympy.Function('y')(t_sym)
        equation_expr = exp["sympy_expr"](y_sym, t_sym)

        sym_solver = SymbolicSolver()
        sym_result = sym_solver.solve_exact(
            equation_expr=equation_expr,
            conditions=exp["conditions"],
            t_range=(0, exp["t_max"]),
            points=500
        )

        if sym_result["success"]:
            print(f"[OK] Solutie de referinta (Simbolica): {sym_result['formula_str']}")
            t_points = np.array(sym_result["data"]["x"])
            y_ref = np.array(sym_result["data"]["y"])
        else:
            print("[INFO] Fallback la solutie Numerica (RK45)...")
            num_solver = NumericalSolver()
            num_result = num_solver.solve_numerical(
                equation_expr=equation_expr,
                conditions=exp["conditions"],
                equation_type=exp["problem_type"],
                t_range=(0, exp["t_max"]),
                points=500
            )
            t_points = np.array(num_result["data"]["x"])
            y_ref = np.array(num_result["data"]["y"])

        # Pregatim figura pentru Loss Curve
        fig_loss, ax_loss = plt.subplots(figsize=(10, 6))
        fig_loss.suptitle(f"{exp['title']} - Evolutia Loss-ului (Medie peste {NUM_RUNS} rulari)", fontsize=14)

        case_results = []

        print(f"\n{'Toleranta':<10} | {'Epoci (Medie)':<15} | {'Acuratete (Medie ± SD)':<25} | {'Eroare L2 (Medie)':<15}")
        print("-" * 75)

        # ==============================================================================
        # B. TESTAREA FIECAREI TOLERANTE
        # ==============================================================================
        for i, tol in enumerate(tolerances):

            runs_data = {
                "epoci": [], "acc": [], "l2": [],
                "history_epochs": [], "history_loss": []
            }

            # Executam cele NUM_RUNS teste independente
            for run_idx in range(NUM_RUNS):
                # Parametri custom: rescriem toleranta din config default
                service = PinnService(custom_params={'tolerance': tol})

                history_epochs = []
                history_loss = []

                # Antrenam modelul. Daca pica numeric (NaN, etc.), inregistram
                # rularea ca esuata (acc=0, l2=inf) si lasam IQR sa o filtreze.
                try:
                    stream = service.train_model_stream(
                        physics_function=exp["physics"],
                        conditions=exp["conditions"],
                        problem_type="ivp",
                        t_max_override=exp["t_max"],
                        callback=lambda e, lp, lb, lt, fd: (e, lp, lb, lt, fd),
                    )

                    for epoch, l_phys, l_bound, l_total, func_data in stream:
                        history_epochs.append(epoch)
                        history_loss.append(max(float(l_total), 1e-16))

                    total_epochs = history_epochs[-1] if history_epochs else 0

                    # Predictie si extragere metrici
                    pinn_data = service.get_function_data(0.0, exp["t_max"], points=500)
                    y_pred = np.array(pinn_data["function_data"]["y"])
                    metrics = service.compute_validation_metrics(t_points, y_pred, y_ref)

                    runs_data["epoci"].append(total_epochs)
                    runs_data["acc"].append(metrics['accuracy_percent'])
                    runs_data["l2"].append(metrics['l2_relative'])
                    runs_data["history_epochs"].append(history_epochs)
                    runs_data["history_loss"].append(history_loss)
                except Exception as run_err:
                    print(f"[WARN] Rularea {run_idx + 1}/{NUM_RUNS} a esuat ({type(run_err).__name__}: {run_err}); o marchez ca outlier.")
                    fallback_epoch = history_epochs[-1] if history_epochs else 0
                    fallback_history = history_loss if history_loss else [1.0]
                    runs_data["epoci"].append(fallback_epoch)
                    runs_data["acc"].append(0.0)
                    runs_data["l2"].append(float('inf'))
                    runs_data["history_epochs"].append(history_epochs if history_epochs else [0])
                    runs_data["history_loss"].append(fallback_history)

            # ==============================================================================
            # C. FILTRARE OUTLIERS (IQR pe acuratete) + CALCUL STATISTICI
            # ==============================================================================
            acc_arr = np.array(runs_data["acc"])
            n_total = len(acc_arr)

            # Cerem minim 4 rulari ca IQR sa aiba sens; sub 4 nu filtram.
            MIN_FOR_IQR = 4
            MIN_SURVIVORS = 3

            if n_total >= MIN_FOR_IQR:
                q1 = np.percentile(acc_arr, 25)
                q3 = np.percentile(acc_arr, 75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                mask = (acc_arr >= lower) & (acc_arr <= upper)
                n_kept = int(mask.sum())

                if n_kept < MIN_SURVIVORS:
                    print(f"[WARN] IQR ar elimina prea multe rulari ({n_total - n_kept}/{n_total}); pastrez toate.")
                    mask = np.ones(n_total, dtype=bool)
                elif n_kept < n_total:
                    removed_vals = acc_arr[~mask]
                    removed_str = ', '.join(f'{v:.2f}%' for v in removed_vals)
                    print(f"[INFO] IQR a eliminat {n_total - n_kept}/{n_total} outlieri "
                          f"(acc: [{removed_str}]; interval valid: [{lower:.2f}%, {upper:.2f}%])")
            else:
                mask = np.ones(n_total, dtype=bool)

            # Aplicam aceeasi masca pe toate metricile, ca rularile sa ramana coerente.
            kept_indices = np.where(mask)[0]
            kept_epoci = [runs_data["epoci"][k] for k in kept_indices]
            kept_acc = [runs_data["acc"][k] for k in kept_indices]
            kept_l2 = [runs_data["l2"][k] for k in kept_indices]
            kept_history_loss = [runs_data["history_loss"][k] for k in kept_indices]

            # --- MODIFICAREA 1: Extragem si epocile filtrate ---
            kept_history_epochs = [runs_data["history_epochs"][k] for k in kept_indices]

            avg_epoci = np.mean(kept_epoci)
            avg_acc = np.mean(kept_acc)
            std_acc = np.std(kept_acc)
            avg_l2 = np.mean(kept_l2)

            # Printam linia in tabelul din consola
            print(f"{tol:<10.1e} | {avg_epoci:<15.0f} | {avg_acc:>7.2f}% ± {std_acc:<5.2f}%       | {avg_l2:<15.2e}")

            # --- PREGATIREA MEDIEI PENTRU GRAFIC (Forward Fill) ---
            # 1. Gasim lungimea maxima (cea mai lunga rulare din cele curente)
            max_epochs_len = max(len(h) for h in kept_history_loss)

            # 2. Extindem (pad) rularile mai scurte cu ultima lor valoare
            padded_losses = []
            for h in kept_history_loss:
                if len(h) < max_epochs_len:
                    padded = h + [h[-1]] * (max_epochs_len - len(h))
                else:
                    padded = h
                padded_losses.append(padded)

            padded_losses = np.array(padded_losses) # Shape: (NUM_RUNS, max_epochs_len)

            # 3. Calculam Media si Deviația Standard la FIECARE epocă (pe coloane)
            mean_loss = np.mean(padded_losses, axis=0)
            std_loss = np.std(padded_losses, axis=0)

            # --- MODIFICAREA 2: Generam axa X cu numerele REALE ale epocilor ---
            longest_epochs_list = max(kept_history_epochs, key=len)
            common_epochs = np.array(longest_epochs_list)

            # 5. Desenam media reala a loss-ului (folosind common_epochs in loc de index simplu)
            ax_loss.plot(
                common_epochs,
                mean_loss,
                color=colors[i],
                label=f"Tol: {tol:.1e} (Acc: {avg_acc:.2f}%)",
                linewidth=2
            )

            # 6. Desenam "Umbra" (Banda de deviatie standard)
            ax_loss.fill_between(
                common_epochs,
                mean_loss - std_loss,
                mean_loss + std_loss,
                color=colors[i],
                alpha=0.15
            )

            # Salvam datele agregate in array-ul final
            case_results.append({
                "toleranta": tol,
                "epoci_medie": avg_epoci,
                "acuratete_medie": avg_acc,
                "acuratete_std": std_acc,
                "eroare_l2_medie": avg_l2
            })

        all_results[case_id] = case_results

        # ==============================================================================
        # D. SALVARE GRAFICE SI JSON
        # ==============================================================================

        # Finalizare Grafic Loss
        ax_loss.set_yscale('log')
        ax_loss.set_xlabel('Numar Epoci (Cost Computational)')
        ax_loss.set_ylabel('Loss Total (Scara Logaritmica)')
        ax_loss.grid(True, which="both", ls="--", alpha=0.5)
        ax_loss.legend()
        plt.tight_layout()
        fig_loss.savefig(f"rezultate_licenta/{case_id}_Loss_Mediat.png", dpi=300)
        plt.close(fig_loss)

        # Generare Bar Chart (Trade-off)
        fig_bar, ax_bar1 = plt.subplots(figsize=(10, 6))

        x_labels = [f"{t:.1e}" for t in tolerances]
        epoci_vals = [r["epoci_medie"] for r in case_results]
        acc_vals = [r["acuratete_medie"] for r in case_results]
        acc_stds = [r["acuratete_std"] for r in case_results]

        # Bara albastra pentru numarul de epoci
        ax_bar1.bar(x_labels, epoci_vals, color='skyblue', alpha=0.7, label='Epoci (Medie)')
        ax_bar1.set_xlabel('Toleranta Ceruta')
        ax_bar1.set_ylabel('Numar Epoci (Cost)', color='blue')
        ax_bar1.tick_params(axis='y', labelcolor='blue')

        # Linia rosie cu Error Bars pentru acuratete
        ax_bar2 = ax_bar1.twinx()
        ax_bar2.errorbar(x_labels, acc_vals, yerr=acc_stds, color='red', marker='o', linewidth=2, capsize=5, label='Acuratete Medie ± SD')
        ax_bar2.set_ylabel('Acuratete (%)', color='red')
        ax_bar2.tick_params(axis='y', labelcolor='red')

        fig_bar.suptitle(f"{exp['title']} - Trade-off (Medie pe {NUM_RUNS} rulari)", fontsize=14)
        fig_bar.savefig(f"rezultate_licenta/{case_id}_Tradeoff_Mediat.png", dpi=300)
        plt.close(fig_bar)

        # Salvare incrementala dupa fiecare caz, ca sa nu pierdem datele daca crapa rularea.
        with open("rezultate_licenta/date_experimente.json", "w") as f:
            json.dump(all_results, f, indent=4)
        print(f"[CHECKPOINT] Rezultate salvate dupa {case_id}.")

    # Salvare finala (redundanta cu cea incrementala, pastrata pentru claritate)
    with open("rezultate_licenta/date_experimente.json", "w") as f:
        json.dump(all_results, f, indent=4)

    print("\n[SUCCES] Toate experimentele s-au terminat!")
    print("Verifica folderul 'rezultate_licenta' pentru grafice si date.")

if __name__ == "__main__":
    run_tolerance_experiments()