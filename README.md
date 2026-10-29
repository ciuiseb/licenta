# Solving Differential Equations via PINNs: A Full-Stack Approach

This repository contains the source code and documentation for my bachelor's thesis at Babeș-Bolyai University. The project introduces a full-stack software platform designed to abstract the implementation of Physics-Informed Neural Networks (PINNs) for solving ordinary differential equations (ODEs). 

By removing the technical barrier of low-level framework configuration, this platform allows users to input mathematical equations in natural text and receive real-time, validated neural network predictions.

## Key Features
* **Dynamic Symbolic Parsing:** Utilizes a custom parser to translate natural mathematical text into executable PyTorch computational graphs dynamically.
* **Real-Time Visualization:** Implements an asynchronous Server-Sent Events (SSE) pipeline to stream and visualize loss convergence live during training without blocking the interface.
* **Hybrid Optimization Engine:** Combines exact Automatic Differentiation with a two-phase optimization strategy, using Adam for global exploration and L-BFGS for high-precision local refinement.
* **Multi-Method Validation:** Simultaneously computes and overlays exact symbolic solutions, high-precision numerical solutions (Runge-Kutta 4(5)), and neural approximations to calculate error metrics automatically.
* **Versatile Problem Solving:** Experimentally validated to solve 12 distinct linear and non-linear systems, handling both Initial Value Problems (IVP) and Boundary Value Problems (BVP) up to the third order.

## Technology Stack
* **[Frontend](https://github.com/ciuiseb/licenta/tree/main/frontend):** React (Single Page Application architecture), Chart.js (high-performance live data visualization), and KaTeX (in-browser LaTeX formula rendering).
* **[Backend](https://github.com/ciuiseb/licenta/tree/main/backend):** Python, Flask (REST API and SSE streaming), PyTorch (PINN architecture and Autograd), SymPy (symbolic parsing), and SciPy (numerical integration reference solutions).

For an in-depth exploration of the mathematical foundations, comprehensive experimental benchmarking, and detailed architectural diagrams, please refer to the [paper itself](https://github.com/ciuiseb/licenta/blob/main/paper.pdf).
