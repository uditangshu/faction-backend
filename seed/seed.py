"""
Script to import JEE Advanced questions from JSON into the database.

Usage:
    python seed/seed.py
    or
    python -m seed.seed

This script will:
1. Parse the JSON data
2. Create/Find Class, Subject, Chapter, Topic entries
3. Create Question entries
4. Create PYQ (Previous Year Problems) entries
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from uuid import UUID

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.Basequestion import (
    Class, Subject, Chapter, Topic, Question,
    Class_level, Subject_Type, QuestionType, DifficultyLevel
)
from app.models.user import TargetExam
from app.models.pyq import PreviousYearProblems
from app.services.question_service import QuestionService
from app.services.pyq_service import PYQService


# JSON data
QUESTIONS_DATA = [
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 1,
        "subject": "phy",
        "type": "MCQ",
        "question": "In a historical experiment to determine Planck's constant, a metal surface was irradiated with light of different wavelengths. The emitted photoelectron energies were measured by applying a stopping potential. The relevant data for the wavelength $(\\lambda)$ of incident light and the corresponding stopping potential $\\left(V_{0}\\right)$ are given below :\n\n\\begin{center}\n\n\\begin{tabular}{cc}\n\n\\hline\n\n$\\lambda(\\mu \\mathrm{m})$ & $V_{0}($ Volt $)$ \\\\\n\n\\hline\n\n0.3 & 2.0 \\\\\n\n0.4 & 1.0 \\\\\n\n0.5 & 0.4 \\\\\n\n\\hline\n\n\\end{tabular}\n\n\\end{center}\n\nGiven that $c=3 \\times 10^{8} \\mathrm{~m} \\mathrm{~s}^{-1}$ and $e=1.6 \\times 10^{-19} \\mathrm{C}$, Planck's constant (in units of $J \\mathrm{~s}$ ) found from such an experiment is\n\n(A) $6.0 \\times 10^{-34}$\n\n(B) $6.4 \\times 10^{-34}$\n\n(C) $6.6 \\times 10^{-34}$\n\n(D) $6.8 \\times 10^{-34}$",
        "gold": "B",
        "chapter": "Modern Physics",
        "topic": "PE (Photoelectric Effect)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 2,
        "subject": "phy",
        "type": "MCQ",
        "question": "A uniform wooden stick of mass $1.6 \\mathrm{~kg}$ and length $l$ rests in an inclined manner on a smooth, vertical wall of height $h(<l)$ such that a small portion of the stick extends beyond the wall. The reaction force of the wall on the stick is perpendicular to the stick. The stick makes an angle of $30^{\\circ}$ with the wall and the bottom of the stick is on a rough floor. The reaction of the wall on the stick is equal in magnitude to the reaction of the floor on the stick. The ratio $h / l$ and the frictional force $f$ at the bottom of the stick are\n\n$\\left(g=10 \\mathrm{~ms} \\mathrm{~s}^{2}\\right)$\n\n(A) $\\frac{h}{l}=\\frac{\\sqrt{3}}{16}, f=\\frac{16 \\sqrt{3}}{3} \\mathrm{~N}$\n\n(B) $\\frac{h}{l}=\\frac{3}{16}, f=\\frac{16 \\sqrt{3}}{3} \\mathrm{~N}$\n\n(C) $\\frac{h}{l}=\\frac{3 \\sqrt{3}}{16}, f=\\frac{8 \\sqrt{3}}{3} \\mathrm{~N}$\n\n(D) $\\frac{h}{l}=\\frac{3 \\sqrt{3}}{16}, f=\\frac{16 \\sqrt{3}}{3} \\mathrm{~N}$",
        "gold": "D",
        "chapter": "Mechanics",
        "topic": "Rotational Motion/Statics"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 6,
        "subject": "phy",
        "type": "MCQ(multiple)",
        "question": "Highly excited states for hydrogen-like atoms (also called Rydberg states) with nuclear charge $Z e$ are defined by their principal quantum number $n$, where $n \\gg 1$. Which of the following statement(s) is(are) true?\n\n(A) Relative change in the radii of two consecutive orbitals does not depend on $Z$\n\n(B) Relative change in the radii of two consecutive orbitals varies as $1 / n$\n\n(C) Relative change in the energy of two consecutive orbitals varies as $1 / n^{3}$\n\n(D) Relative change in the angular momenta of two consecutive orbitals varies as $1 / n$",
        "gold": "ABD",
        "chapter": "Modern Physics",
        "topic": "Atomic Structure (Bohr's Model)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 8,
        "subject": "phy",
        "type": "MCQ(multiple)",
        "question": "An incandescent bulb has a thin filament of tungsten that is heated to high temperature by passing an electric current. The hot filament emits black-body radiation. The filament is observed to break up at random locations after a sufficiently long time of operation due to non-uniform evaporation of tungsten from the filament. If the bulb is powered at constant voltage, which of the following statement(s) is(are) true?\n\n(A) The temperature distribution over the filament is uniform\n\n(B) The resistance over small sections of the filament decreases with time\n\n(C) The filament emits more light at higher band of frequencies before it breaks up\n\n(D) The filament consumes less electrical power towards the end of the life of the bulb",
        "gold": "CD",
        "chapter": "Thermo & Current Elec.",
        "topic": "Black Body Rad. & Joule Heating"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 9,
        "subject": "phy",
        "type": "MCQ(multiple)",
        "question": "A plano-convex lens is made of a material of refractive index $n$. When a small object is placed $30 \\mathrm{~cm}$ away in front of the curved surface of the lens, an image of double the size of the object is produced. Due to reflection from the convex surface of the lens, another faint image is observed at a distance of $10 \\mathrm{~cm}$ away from the lens. Which of the following statement(s) is(are) true?\n\n(A) The refractive index of the lens is 2.5\n\n(B) The radius of curvature of the convex surface is $45 \\mathrm{~cm}$\n\n(C) The faint image is erect and real\n\n(D) The focal length of the lens is $20 \\mathrm{~cm}$",
        "gold": "AD",
        "chapter": "Optics",
        "topic": "Ray Optics (Lenses/Refraction)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 10,
        "subject": "phy",
        "type": "MCQ(multiple)",
        "question": "A length-scale $(l)$ depends on the permittivity $(\\varepsilon)$ of a dielectric material, Boltzmann constant $\\left(k_{B}\\right)$, the absolute temperature $(T)$, the number per unit volume $(n)$ of certain charged particles, and the charge $(q)$ carried by each of the particles. Which of the following expression(s) for $l$ is(are) dimensionally correct?\n\n(A) $l=\\sqrt{\\left(\\frac{n q^{2}}{\\varepsilon k_{B} T}\\right)}$\n\n(B) $l=\\sqrt{\\left(\\frac{\\varepsilon k_{B} T}{n q^{2}}\\right)}$\n\n(C) $l=\\sqrt{\\left(\\frac{q^{2}}{\\varepsilon n^{2 / 3} k_{B} T}\\right)}$\n\n(D) $l=\\sqrt{\\left(\\frac{q^{2}}{\\varepsilon n^{1 / 3} k_{B} T}\\right)}$",
        "gold": "BD",
        "chapter": "General Physics",
        "topic": "Units and Dimensions"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 12,
        "subject": "phy",
        "type": "MCQ(multiple)",
        "question": "The position vector $\\vec{r}$ of a particle of mass $m$ is given by the following equation\n\n\\[\n\\vec{r}(t)=\\alpha t^{3} \\hat{i}+\\beta t^{2} \\hat{j}\n\\]\n\nwhere $\\alpha=10 / 3 \\mathrm{~m} \\mathrm{~s}^{-3}, \\beta=5 \\mathrm{~m} \\mathrm{~s}^{-2}$ and $m=0.1 \\mathrm{~kg}$. At $t=1 \\mathrm{~s}$, which of the following statement(s) is(are) true about the particle?\n\n(A) The velocity $\\vec{v}$ is given by $\\vec{v}=(10 \\hat{i}+10 \\hat{j}) \\mathrm{ms}^{-1}$\n\n(B) The angular momentum $\\vec{L}$ with respect to the origin is given by $\\vec{L}=-(5 / 3) \\hat{k} \\mathrm{~N} \\mathrm{~m}$\n\n(C) The force $\\vec{F}$ is given by $\\vec{F}=(\\hat{i}+2 \\hat{j}) \\mathrm{N}$\n\n(D) The torque $\\vec{\\tau}$ with respect to the origin is given by $\\vec{\\tau}=-(20 / 3) \\hat{k} \\mathrm{~N} \\mathrm{~m}$",
        "gold": "ABD",
        "chapter": "Mechanics",
        "topic": "Kinematics/Dynamics/RM"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 14,
        "subject": "phy",
        "type": "Integer",
        "question": "A metal is heated in a furnace where a sensor is kept above the metal surface to read the power radiated $(P)$ by the metal. The sensor has a scale that displays $\\log _{2}\\left(P / P_{0}\\right)$, where $P_{0}$ is a constant. When the metal surface is at a temperature of $487^{\\circ} \\mathrm{C}$, the sensor shows a value 1. Assume that the emissivity of the metallic surface remains constant. What is the value displayed by the sensor when the temperature of the metal surface is raised to $2767{ }^{\\circ} \\mathrm{C}$ ?",
        "gold": "9",
        "chapter": "Heat and Thermodynamics",
        "topic": "Thermal Properties/BBR"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 15,
        "subject": "phy",
        "type": "Integer",
        "question": "The isotope ${ }_{5}^{12} \\mathrm{~B}$ having a mass 12.014 u undergoes $\\beta$-decay to ${ }_{6}^{12} \\mathrm{C}$. ${ }_{6}^{12} \\mathrm{C}$ has an excited state of the nucleus $\\left({ }_{6}^{12} \\mathrm{C}^{*}\\right)$ at $4.041 \\mathrm{MeV}$ above its ground state. If ${ }_{5}^{12} \\mathrm{~B}$ decays to ${ }_{6}^{12} \\mathrm{C}^{*}$, what is the maximum kinetic energy of the $\\beta$-particle in units of $\\mathrm{MeV}$?\n\n$\\left(1 \\mathrm{u}=931.5 \\mathrm{MeV} / c^{2}\\right.$, where $c$ is the speed of light in vacuum).",
        "gold": "9",
        "chapter": "Modern Physics",
        "topic": "Nuclear Physics (Decay/Q-value)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 16,
        "subject": "phy",
        "type": "Integer",
        "question": "A hydrogen atom in its ground state is irradiated by light of wavelength 970 A. Taking $h c / e=1.237 \\times 10^{-6} \\mathrm{eV} \\mathrm{m}$ and the ground state energy of hydrogen atom as $-13.6 \\mathrm{eV}$, what is the number of lines present in the emission spectrum?",
        "gold": "6",
        "chapter": "Modern Physics",
        "topic": "Atomic Structure (Spectrum)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 17,
        "subject": "phy",
        "type": "Integer",
        "question": "Consider two solid spheres $\\mathrm{P}$ and $\\mathrm{Q}$ each of density $8 \\mathrm{gm} \\mathrm{cm}^{-3}$ and diameters $1 \\mathrm{~cm}$ and $0.5 \\mathrm{~cm}$, respectively. Sphere $P$ is dropped into a liquid of density $0.8 \\mathrm{gm} \\mathrm{cm}^{-3}$ and viscosity $\\eta=3$ poiseulles. Sphere $Q$ is dropped into a liquid of density $1.6 \\mathrm{gm} \\mathrm{cm}^{-3}$ and viscosity $\\eta=2$ poiseulles. What is the ratio of the terminal velocities of $P$ and $Q$?",
        "gold": "3",
        "chapter": "Mechanics",
        "topic": "Fluid Mech (Viscosity/Term. Vel.)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 18,
        "subject": "phy",
        "type": "Integer",
        "question": "Two inductors $L_{1}$ (inductance $1 \\mathrm{mH}$, internal resistance $3 \\Omega$ ) and $L_{2}$ (inductance $2 \\mathrm{mH}$, internal resistance $4 \\Omega$ ), and a resistor $R$ (resistance $12 \\Omega$ ) are all connected in parallel across a $5 \\mathrm{~V}$ battery. The circuit is switched on at time $t=0$. What is the ratio of the maximum to the minimum current $\\left(I_{\\max } / I_{\\min }\\right)$ drawn from the battery?",
        "gold": "8",
        "chapter": "Electromagnetism",
        "topic": "AC Circuits/EMI (RL Transient)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 20,
        "subject": "chem",
        "type": "MCQ",
        "question": "One mole of an ideal gas at $300 \\mathrm{~K}$ in thermal contact with surroundings expands isothermally from $1.0 \\mathrm{~L}$ to $2.0 \\mathrm{~L}$ against a constant pressure of $3.0 \\mathrm{~atm}$. In this process, the change in entropy of surroundings $\\left(\\Delta S_{\\text {surr }}\\right)$ in $\\mathrm{J} \\mathrm{K}^{-1}$ is\n\n(1 $\\mathrm{L} \\operatorname{atm}=101.3 \\mathrm{~J})$\n\n(A) 5.763\n\n(B) 1.013\n\n(C) -1.013\n\n(D) -5.763",
        "gold": "C",
        "chapter": "Physical Chemistry",
        "topic": "Thermo: Entropy ($\\Delta S$)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 21,
        "subject": "chem",
        "type": "MCQ",
        "question": "The increasing order of atomic radii of the following Group 13 elements is\n\n(A) $\\mathrm{Al}<\\mathrm{Ga}<\\mathrm{In}<\\mathrm{Tl}$\n\n(B) $\\mathrm{Ga}<\\mathrm{Al}<\\mathrm{In}<\\mathrm{Tl}$\n\n(C) $\\mathrm{Al}<\\mathrm{In}<\\mathrm{Ga}<\\mathrm{Tl}$\n\n(D) $\\mathrm{Al}<\\mathrm{Ga}<\\mathrm{Tl}<\\mathrm{In}$",
        "gold": "B",
        "chapter": "Inorganic Chemistry",
        "topic": "Periodicity: Atomic Radii"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 22,
        "subject": "chem",
        "type": "MCQ",
        "question": "Among $[\\mathrm{Ni(CO)}_{4}]$, $[\\mathrm{NiCl}_{4}]^{2-}$, $[\\mathrm{Co(NH_3)_{4}Cl_2}]\\mathrm{Cl}$, $\\mathrm{Na_3}[\\mathrm{CoF_6}]$, $\\mathrm{Na_2O_2}$ and $\\mathrm{CsO_2}$ number of paramagnetic compounds is\n\n(A) 2\n\n(B) 3\n\n(C) 4\n\n(D) 5",
        "gold": "B",
        "chapter": "Inorganic Chemistry",
        "topic": "Coord. Comp/p-Block ($\\mathrm{d}$-config/Hybrid)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 23,
        "subject": "chem",
        "type": "MCQ",
        "question": "On complete hydrogenation, natural rubber produces\n\n(A) ethylene-propylene copolymer\n\n(B) vulcanised rubber\n\n(C) polypropylene\n\n(D) polybutylene",
        "gold": "A",
        "chapter": "Organic Chemistry",
        "topic": "Polymers (Natural Rubber)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 24,
        "subject": "chem",
        "type": "MCQ(multiple)",
        "question": "According to the Arrhenius equation,\n\n(A) a high activation energy usually implies a fast reaction.\n\n(B) rate constant increases with increase in temperature. This is due to a greater number of collisions whose energy exceeds the activation energy. (C) higher the magnitude of activation energy, stronger is the temperature dependence of\n\nthe rate constant.\n\n(D) the pre-exponential factor is a measure of the rate at which collisions occur, irrespective of their energy.",
        "gold": "BCD",
        "chapter": "Physical Chemistry",
        "topic": "Kinetics: Arrhenius Eq./$E_a$"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 25,
        "subject": "chem",
        "type": "MCQ(multiple)",
        "question": "A plot of the number of neutrons $(N)$ against the number of protons $(P)$ of stable nuclei exhibits upward deviation from linearity for atomic number, $Z>20$. For an unstable nucleus having $N / P$ ratio less than 1 , the possible mode(s) of decay is(are)\n\n(A) $\\beta^{-}$-decay $(\\beta$ emission)\n\n(B) orbital or $K$-electron capture\n\n(C) neutron emission\n\n(D) $\\beta^{+}$-decay (positron emission)",
        "gold": "BD",
        "chapter": "Physical Chemistry",
        "topic": "Nuclear Chem: Decay Modes"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 26,
        "subject": "chem",
        "type": "MCQ(multiple)",
        "question": "The crystalline form of borax has\n\n(A) tetranuclear $\\left[\\mathrm{B}_{4} \\mathrm{O}_{5}(\\mathrm{OH})_{4}\\right]^{2-}$ unit\n\n(B) all boron atoms in the same plane\n\n(C) equal number of $s p^{2}$ and $s p^{3}$ hybridized boron atoms\n\n(D) one terminal hydroxide per boron atom",
        "gold": "ACD",
        "chapter": "Inorganic Chemistry",
        "topic": "p-Block: Borax Structure"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 27,
        "subject": "chem",
        "type": "MCQ(multiple)",
        "question": "The compound(s) with TWO lone pairs of electrons on the central atom is(are)\n\n(A) $\\mathrm{BrF}_{5}$\n\n(B) $\\mathrm{ClF}_{3}$\n\n(C) $\\mathrm{XeF}_{4}$\n\n(D) $\\mathrm{SF}_{4}$",
        "gold": "BC",
        "chapter": "Inorganic Chemistry",
        "topic": "Chem. Bonding: VSEPR/Hybrid."
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 28,
        "subject": "chem",
        "type": "MCQ(multiple)",
        "question": "The reagent(s) that can selectively precipitate $\\mathrm{S}^{2-}$ from a mixture of $\\mathrm{S}^{2-}$ and $\\mathrm{SO}_{4}^{2-}$ in aqueous solution is(are)\n\n(A) $\\mathrm{CuCl}_{2}$\n\n(B) $\\mathrm{BaCl}_{2}$\n\n(C) $\\mathrm{Pb}\\left(\\mathrm{OOCCH}_{3}\\right)_{2}$\n\n(D) $\\mathrm{Na}_{2}\\left[\\mathrm{Fe}(\\mathrm{CN})_{5} \\mathrm{NO}\\right]$",
        "gold": "A",
        "chapter": "Inorganic Chemistry",
        "topic": "Qualitative Analysis: $\\mathrm{K_{sp}}$"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 32,
        "subject": "chem",
        "type": "Integer",
        "question": "The mole fraction of a solute in a solution is 0.1 . At $298 \\mathrm{~K}$, molarity of this solution is the same as its molality. Density of this solution at $298 \\mathrm{~K}$ is $2.0 \\mathrm{~g} \\mathrm{~cm}^{-3}$. What is the ratio of the molecular weights of the solute and solvent, $\\left(\\frac{M W_{\\text {solute }}}{M W_{\\text {solvent }}}\\right)$?",
        "gold": "9",
        "chapter": "Physical Chemistry",
        "topic": "Solutions: Concentration Terms"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 33,
        "subject": "chem",
        "type": "Integer",
        "question": "The diffusion coefficient of an ideal gas is proportional to its mean free path and mean speed. The absolute temperature of an ideal gas is increased 4 times and its pressure is increased 2 times. As a result, the diffusion coefficient of this gas increases $x$ times. What is the value of $x$?",
        "gold": "4",
        "chapter": "Physical Chemistry",
        "topic": "Gaseous State: Diffusion"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 34,
        "subject": "chem",
        "type": "Integer",
        "question": "In neutral or faintly alkaline solution, 8 moles of permanganate anion quantitatively oxidize thiosulphate anions to produce $\\mathbf{X}$ moles of a sulphur containing product. What is the magnitude of $\\mathbf{X}$?",
        "gold": "6",
        "chapter": "Physical Chemistry",
        "topic": "Redox Reactions/Stoichiometry"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 37,
        "subject": "math",
        "type": "MCQ",
        "question": "Let $-\\frac{\\pi}{6}<\\theta<-\\frac{\\pi}{12}$. Suppose $\\alpha_{1}$ and $\\beta_{1}$ are the roots of the equation $x^{2}-2 x \\sec \\theta+1=0$ and $\\alpha_{2}$ and $\\beta_{2}$ are the roots of the equation $x^{2}+2 x \\tan \\theta-1=0$. If $\\alpha_{1}>\\beta_{1}$ and $\\alpha_{2}>\\beta_{2}$, then $\\alpha_{1}+\\beta_{2}$ equals\n\n(A) $2(\\sec \\theta-\\tan \\theta)$\n\n(B) $2 \\sec \\theta$\n\n(C) $-2 \\tan \\theta$\n\n(D) 0",
        "gold": "C",
        "chapter": "Algebra & Trigonometry",
        "topic": "Quad. Eq. & Trig. Identities"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 38,
        "subject": "math",
        "type": "MCQ",
        "question": "A debate club consists of 6 girls and 4 boys. A team of 4 members is to be selected from this club including the selection of a captain (from among these 4 members) for the team. If the team has to include at most one boy, then the number of ways of selecting the team is\n\n(A) 380\n\n(B) 320\n\n(C) 260\n\n(D) 95",
        "gold": "A",
        "chapter": "Algebra",
        "topic": "Permutations & Combinations (P&C)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 39,
        "subject": "math",
        "type": "MCQ",
        "question": "Let $S=\\left\\{x \\in(-\\pi, \\pi): x \\neq 0, \\pm \\frac{\\pi}{2}\\right\\}$. The sum of all distinct solutions of the equation $\\sqrt{3} \\sec x+\\operatorname{cosec} x+2(\\tan x-\\cot x)=0$ in the set $S$ is equal to\n\n(A) $-\\frac{7 \\pi}{9}$\n\n(B) $-\\frac{2 \\pi}{9}$\n\n(C) 0\n\n(D) $\\frac{5 \\pi}{9}$",
        "gold": "C",
        "chapter": "Trigonometry",
        "topic": "Trigonometric Equations"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 40,
        "subject": "math",
        "type": "MCQ",
        "question": "A computer producing factory has only two plants $T_{1}$ and $T_{2}$. Plant $T_{1}$ produces $20 \\%$ and plant $T_{2}$ produces $80 \\%$ of the total computers produced. $7 \\%$ of computers produced in the factory turn out to be defective. It is known that\n\n$P$ (computer turns out to be defective given that it is produced in plant $T_{1}$ )\n\n$=10 P\\left(\\right.$ computer turns out to be defective given that it is produced in plant $\\left.T_{2}\\right)$,\n\nwhere $P(E)$ denotes the probability of an event $E$. A computer produced in the factory is randomly selected and it does not turn out to be defective. Then the probability that it is produced in plant $T_{2}$ is\n\n(A) $\\frac{36}{73}$\n\n(B) $\\frac{47}{79}$\n\n(C) $\\frac{78}{93}$\n\n(D) $\\frac{75}{83}$",
        "gold": "C",
        "chapter": "Algebra",
        "topic": "Probability (Bayes/Total Prob.)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 41,
        "subject": "math",
        "type": "MCQ",
        "question": "The least value of $\\alpha \\in \\mathbb{R}$ for which $4 \\alpha x^{2}+\\frac{1}{x} \\geq 1$, for all $x>0$, is\n\n(A) $\\frac{1}{64}$\n\n(B) $\\frac{1}{32}$\n\n(C) $\\frac{1}{27}$\n\n(D) $\\frac{1}{25}$",
        "gold": "C",
        "chapter": "Calculus",
        "topic": "AOD (Inequalities/Minima)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 42,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "Consider a pyramid $O P Q R S$ located in the first octant $(x \\geq 0, y \\geq 0, z \\geq 0)$ with $O$ as origin, and $O P$ and $O R$ along the $x$-axis and the $y$-axis, respectively. The base $O P Q R$ of the pyramid is a square with $O P=3$. The point $S$ is directly above the mid-point $T$ of diagonal $O Q$ such that $T S=3$. Then\n\n(A) the acute angle between $O Q$ and $O S$ is $\\frac{\\pi}{3}$\n\n(B) the equation of the plane containing the triangle $O Q S$ is $x-y=0$\n\n(C) the length of the perpendicular from $P$ to the plane containing the triangle $O Q S$ is $\\frac{3}{\\sqrt{2}}$\n\n(D) the perpendicular distance from $O$ to the straight line containing $R S$ is $\\sqrt{\\frac{15}{2}}$",
        "gold": "BCD",
        "chapter": "Coordinate Geometry",
        "topic": "3D Geometry/Vector Algebra"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 43,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "Let $f:(0, \\infty) \\rightarrow \\mathbb{R}$ be a differentiable function such that $f^{\\prime}(x)=2-\\frac{f(x)}{x}$ for all $x \\in(0, \\infty)$ and $f(1) \\neq 1$. Then\n\n(A) $\\lim _{x \\rightarrow 0+} f^{\\prime}\\left(\\frac{1}{x}\\right)=1$\n\n(B) $\\lim _{x \\rightarrow 0+} x f\\left(\\frac{1}{x}\\right)=2$\n\n(C) $\\lim _{x \\rightarrow 0+} x^{2} f^{\\prime}(x)=0$\n\n(D) $|f(x)| \\leq 2$ for all $x \\in(0,2)$",
        "gold": "A",
        "chapter": "Calculus",
        "topic": "Differential Eq.: Linear ODE"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 44,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "Let $P=\\left[\\begin{array}{ccc}3 & -1 & -2 \\\\ 2 & 0 & \\alpha \\\\ 3 & -5 & 0\\end{array}\\right]$, where $\\alpha \\in \\mathbb{R}$. Suppose $Q=\\left[q_{i j}\\right]$ is a matrix such that $P Q=k I$, where $k \\in \\mathbb{R}, k \\neq 0$ and $I$ is the identity matrix of order 3 . If $q_{23}=-\\frac{k}{8}$ and $\\operatorname{det}(Q)=\\frac{k^{2}}{2}$, then\n\n(A) $\\alpha=0, k=8$\n\n(B) $4 \\alpha-k+8=0$\n\n(C) $\\operatorname{det}(P \\operatorname{adj}(Q))=2^{9}$\n\n(D) $\\operatorname{det}(Q \\operatorname{adj}(P))=2^{13}$",
        "gold": "BC",
        "chapter": "Algebra",
        "topic": "Matrices & Determinants (Adj/Inv)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 45,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "In a triangle $X Y Z$, let $x, y, z$ be the lengths of sides opposite to the angles $X, Y, Z$, respectively, and $2 s=x+y+z$. If $\\frac{s-x}{4}=\\frac{s-y}{3}=\\frac{s-z}{2}$ and area of incircle of the triangle $X Y Z$ is $\\frac{8 \\pi}{3}$, then\n\n(A) area of the triangle $X Y Z$ is $6 \\sqrt{6}$\n\n(B) the radius of circumcircle of the triangle $X Y Z$ is $\\frac{35}{6} \\sqrt{6}$\n\n(C) $\\sin \\frac{X}{2} \\sin \\frac{Y}{2} \\sin \\frac{Z}{2}=\\frac{4}{35}$\n\n(D) $\\sin ^{2}\\left(\\frac{X+Y}{2}\\right)=\\frac{3}{5}$",
        "gold": "ACD",
        "chapter": "Trig. & Geometry",
        "topic": "Properties of Triangle (POT)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 46,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "A solution curve of the differential equation $\\left(x^{2}+x y+4 x+2 y+4\\right) \\frac{d y}{d x}-y^{2}=0, x>0$, passes through the point $(1,3)$. Then the solution curve\n\n(A) intersects $y=x+2$ exactly at one point\n\n(B) intersects $y=x+2$ exactly at two points\n\n(C) intersects $y=(x+2)^{2}$\n\n(D) does NO'T intersect $y=(x+3)^{2}$",
        "gold": "AD",
        "chapter": "Calculus",
        "topic": "Differential Eq.: Var. Separable"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 47,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "Let $f: \\mathbb{R} \\rightarrow \\mathbb{R}, \\quad g: \\mathbb{R} \\rightarrow \\mathbb{R}$ and $h: \\mathbb{R} \\rightarrow \\mathbb{R}$ be differentiable functions such that $f(x)=x^{3}+3 x+2, g(f(x))=x$ and $h(g(g(x)))=x$ for all $x \\in \\mathbb{R}$. Then\n\n(A) $\\quad g^{\\prime}(2)=\\frac{1}{15}$\n\n(B) $h^{\\prime}(1)=666$\n\n(C) $h(0)=16$\n\n(D) $h(g(3))=36$",
        "gold": "BC",
        "chapter": "Calculus",
        "topic": "Functions/Differentiability"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 48,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "The circle $C_{1}: x^{2}+y^{2}=3$, with centre at $O$, intersects the parabola $x^{2}=2 y$ at the point $P$ in the first quadrant. Let the tangent to the circle $C_{1}$ at $P$ touches other two circles $C_{2}$ and $C_{3}$ at $R_{2}$ and $R_{3}$, respectively. Suppose $C_{2}$ and $C_{3}$ have equal radii $2 \\sqrt{3}$ and centres $Q_{2}$ and $Q_{3}$, respectively. If $Q_{2}$ and $Q_{3}$ lie on the $y$-axis, then\n\n(A) $Q_{2} Q_{3}=12$\n\n(B) $\\quad R_{2} R_{3}=4 \\sqrt{6}$\n\n(C) area of the triangle $O R_{2} R_{3}$ is $6 \\sqrt{2}$\n\n(D) area of the triangle $P Q_{2} Q_{3}$ is $4 \\sqrt{2}$",
        "gold": "ABC",
        "chapter": "Coordinate Geometry",
        "topic": "Circle & Parabola"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 49,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "Let $R S$ be the diameter of the circle $x^{2}+y^{2}=1$, where $S$ is the point $(1,0)$. Let $P$ be a variable point (other than $R$ and $S$ ) on the circle and tangents to the circle at $S$ and $P$ meet at the point $Q$. The normal to the circle at $P$ intersects a line drawn through $Q$ parallel to $R S$ at point $E$. Then the locus of $E$ passes through the point(s)\n\n(A) $\\left(\\frac{1}{3}, \\frac{1}{\\sqrt{3}}\\right)$\n\n(B) $\\left(\\frac{1}{4}, \\frac{1}{2}\\right)$\n\n(C) $\\left(\\frac{1}{3},-\\frac{1}{\\sqrt{3}}\\right)$\n\n(D) $\\left(\\frac{1}{4},-\\frac{1}{2}\\right)$",
        "gold": "AC",
        "chapter": "Coordinate Geometry",
        "topic": "Circles: Tangent/Locus"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 50,
        "subject": "math",
        "type": "MCQ(multiple)",
        "question": "Let $\\operatorname{det}(A)$ be the determinant of a square matrix $A$ of order 3 and $\\operatorname{det}(A)=3$. If $Q=A^3 + 2A^2 + A$ and $A^T A = I$, where $I$ is the identity matrix of order 3, then $\\operatorname{det}(Q)$ is equal to...",
        "gold": "8",
        "chapter": "Algebra",
        "topic": "Determinants (Properties)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 51,
        "subject": "math",
        "type": "Integer",
        "question": "The coefficient of $x^{9}$ in the expansion of $(1+x)\\left(1+x^{2}\\right)\\left(1+x^{3}\\right) \\ldots\\left(1+x^{100}\\right)$ is...",
        "gold": "8",
        "chapter": "Algebra",
        "topic": "Binomial Theorem (BT)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 52,
        "subject": "math",
        "type": "Integer",
        "question": "The number of distinct roots of the equation $\\int_{0}^{x} \\frac{t^{2}}{1+t^{4}} d t=2 x^{2}$ is...",
        "gold": "1",
        "chapter": "Calculus",
        "topic": "Definite Integrals (FTC)"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 53,
        "subject": "math",
        "type": "Integer",
        "question": "The value of $\\lim _{x \\rightarrow 0} \\frac{(1-\\cos 2 x)^{2}}{2 x \\tan x-x^{2} \\tan ^{2} x}$ is...",
        "gold": "2",
        "chapter": "Calculus",
        "topic": "Limits"
    },
    {
        "description": "JEE Adv 2016 Paper 1",
        "index": 54,
        "subject": "math",
        "type": "Integer",
        "question": "Let $\\omega \\neq 1$ be a cube root of unity. Let $A$ and $B$ be two $3 \\times 3$ matrices such that $A=\\left[\\begin{array}{ccc} 1 & \\omega & \\omega^{2} \\\\ \\omega & \\omega^{2} & 1 \\\\ \\omega^{2} & 1 & \\omega \\end{array}\\right]$ and $B=\\left[\\begin{array}{ccc} 1 & 1 & 1 \\\\ 1 & \\omega & \\omega^{2} \\\\ 1 & \\omega^{2} & \\omega \\end{array}\\right]$. If $\\operatorname{det}(A+B)=k \\operatorname{det}(A)$, then the value of $k$ is...",
        "gold": "0",
        "chapter": "Algebra",
        "topic": "Complex No. & Matrices"
    },
    {
        "description": "JEE Adv 2016 Paper 2",
        "index": "Paper 2, 1",
        "subject": "phy",
        "type": "Paragraph",
        "question": "The electrostatic energy of $Z$ protons uniformly distributed throughout a spherical nucleus of radius $R$ is given by\n\n\\[\nE=\\frac{3}{5} \\frac{Z(Z-1) e^{2}}{4 \\pi \\varepsilon_{0} R}\n\\]\n\nThe measured masses of the neutron, ${ }_{1}^{1} \\mathrm{H},{ }_{7}^{15} \\mathrm{~N}$ and ${ }_{8}^{15} \\mathrm{O}$ are $1.008665 \\mathrm{u}, 1.007825 \\mathrm{u}$, $15.000109 \\mathrm{u}$ and $15.003065 \\mathrm{u}$, respectively. Given that the radii of both the ${ }_{7}^{15} \\mathrm{~N}$ and ${ }_{8}^{15} \\mathrm{O}$ nuclei are same, $1 \\mathrm{u}=931.5 \\mathrm{MeV} / c^{2}$ ( $c$ is the speed of light) and $e^{2} /\\left(4 \\pi \\varepsilon_{0}\\right)=1.44 \\mathrm{MeV} \\mathrm{fm}$. Assuming that the difference between the binding energies of ${ }_{7}^{15} \\mathrm{~N}$ and ${ }_{8}^{15} \\mathrm{O}$ is purely due to the electrostatic energy, the radius of either of the nuclei is $\\left(1 \\mathrm{fm}=10^{-15} \\mathrm{~m}\\right)$",
        "gold": "3.37",
        "chapter": "Modern Physics",
        "topic": "Nuclear Physics (Binding Energy)"
    },
    {
        "description": "JEE Adv 2016 Paper 2",
        "index": "Paper 2, 2",
        "subject": "phy",
        "type": "Paragraph",
        "question": "A radioactive nucleus (initial number of nuclei $N_{0}$ ) decays to form a stable nuclide. The ratio of decayed nuclei to non-decayed nuclei at time $t$ is $R$. Which of the following statement(s) is(are) true?\n\n(A) $R=\\frac{N_{0}}{N} e^{-\\lambda t}$\n\n(B) The time at which the number of decayed nuclei is half of the initial number is $t=\\frac{\\ln 2}{\\lambda}$\n\n(C) The time at which the ratio $R=0.5$ is $t=\\frac{\\ln 3}{\\lambda}$\n\n(D) The ratio of the activity at time $t$ to the activity at time $t=0$ is $1 /(R+1)$",
        "gold": "BD",
        "chapter": "Modern Physics",
        "topic": "Nuclear Physics (Radioactivity)"
    },
    {
        "description": "JEE Adv 2016 Paper 2",
        "index": "Paper 2, 3",
        "subject": "phy",
        "type": "Paragraph",
        "question": "A certain amount of an ideal gas passes from state A to state B as shown in the given $P-V$ diagram. The maximum internal energy is achieved at a point $C$ on the path. Which of the following statement(s) is(are) true?\n\n(A) The heat given to the gas in the process $A \\rightarrow B$ is equal to the work done by the gas from $A \\rightarrow B$\n\n(B) The temperature of the gas is maximum at the point $C$\n\n(C) The work done by the gas in the process $A \\rightarrow C$ is greater than the work done by the gas in the process $C \\rightarrow B$\n\n(D) The process $A \\rightarrow B$ is adiabatic",
        "gold": "B",
        "chapter": "Heat and Thermodynamics",
        "topic": "Thermodynamics (First Law)"
    }
]


# Mapping functions
def map_subject(subject_str: str) -> Subject_Type:
    """Map subject string to Subject_Type enum"""
    mapping = {
        "phy": Subject_Type.PHYSICS,
        "chem": Subject_Type.CHEMISTRY,
        "math": Subject_Type.MATHS,
        "bio": Subject_Type.BIOLOGY,
    }
    return mapping.get(subject_str.lower(), Subject_Type.PHYSICS)


def map_question_type(type_str: str, gold_answer: Optional[str] = None) -> QuestionType:
    """Map question type string to QuestionType enum"""
    type_lower = type_str.lower()
    if "mcq" in type_lower and "multiple" in type_lower:
        return QuestionType.SCQ
    elif "mcq" in type_lower:
        return QuestionType.MCQ
    elif "integer" in type_lower:
        return QuestionType.INTEGER
    elif "paragraph" in type_lower:
        # For paragraph questions, determine type based on answer format
        if gold_answer:
            # If answer is a single letter (A, B, C, D), it's MCQ
            if len(gold_answer) == 1 and gold_answer.isalpha():
                return QuestionType.MCQ
            # If answer is multiple letters (AB, CD, etc.), it's SCQ
            elif len(gold_answer) > 1 and all(c.isalpha() for c in gold_answer):
                return QuestionType.SCQ
            # If answer is numeric, it might be integer (but paragraph usually has options)
            # Default to MCQ for paragraph with numeric answer
            else:
                return QuestionType.MCQ
        return QuestionType.MCQ  # Default for paragraph
    else:
        return QuestionType.MCQ  # Default


def extract_exam_type(description: str) -> List[TargetExam]:
    """Extract exam type from description"""
    exam_types = []
    if "JEE Adv" in description or "JEE Advanced" in description:
        exam_types.append(TargetExam.JEE_ADVANCED)
    if "JEE Main" in description or "JEE Mains" in description:
        exam_types.append(TargetExam.JEE_MAINS)
    if "NEET" in description:
        exam_types.append(TargetExam.NEET)
    if not exam_types:
        exam_types.append(TargetExam.JEE_ADVANCED)  # Default for JEE Adv 2016
    return exam_types


def extract_year(description: str) -> int:
    """Extract year from description (e.g., 'JEE Adv 2016 Paper 1' -> 2016)"""
    # Look for 4-digit year pattern (1900-2099)
    year_match = re.search(r'\b(19|20)\d{2}\b', description)
    if year_match:
        return int(year_match.group())
    # Default to 2016 if no year found
    return 2016


def extract_options_from_question(question_text: str) -> List[str]:
    """Extract MCQ/SCQ options from question text"""
    options = []
    
    # First, try to find options in the format (A) ... (B) ... (C) ... (D) ...
    # Look for the pattern where options start
    lines = question_text.split('\n')
    option_start_idx = None
    
    # Find where options start (look for first occurrence of (A))
    for i, line in enumerate(lines):
        if re.search(r'^\([A-D]\)', line.strip()):
            option_start_idx = i
            break
    
    if option_start_idx is not None:
        # Extract options from this point
        current_option = None
        current_letter = None
        
        for i in range(option_start_idx, len(lines)):
            line = lines[i].strip()
            
            # Check if this line starts a new option
            match = re.match(r'^\(([A-D])\)\s*(.*)', line)
            if match:
                # Save previous option if exists
                if current_option is not None:
                    options.append(current_option.strip())
                
                # Start new option
                current_letter = match.group(1)
                current_option = match.group(2).strip()
            elif current_option is not None and line:
                # Continue current option (multi-line option)
                current_option += ' ' + line
        
        # Add last option
        if current_option is not None:
            options.append(current_option.strip())
    
    # If still no options found, try a more aggressive pattern
    if not options:
        # Pattern to match (A) ... (B) ... (C) ... (D) ... with multiline content
        pattern = r'\(([A-D])\)\s*([^\n\(]+(?:\n(?!\([A-D]\))[^\n\(]+)*)'
        matches = re.findall(pattern, question_text, re.MULTILINE)
        
        for letter, content in matches:
            # Clean up the content
            content = content.strip()
            # Remove excessive whitespace
            content = re.sub(r'\s+', ' ', content)
            if content:
                options.append(content)
    
    # Ensure we have exactly 4 options (A, B, C, D)
    if len(options) < 4:
        # Try to find options that might be on same line or differently formatted
        # Look for numbered options (1), (2), (3), (4) and convert
        numbered_pattern = r'\(([1-4])\)\s*([^\n\(]+)'
        numbered_matches = re.findall(numbered_pattern, question_text)
        if numbered_matches and len(numbered_matches) >= 4:
            options = [content.strip() for _, content in sorted(numbered_matches, key=lambda x: int(x[0]))]
    
    return options[:4]  # Return at most 4 options


def map_answer_to_indices(gold: str, question_type: QuestionType) -> Tuple[Optional[int | List[int]], Optional[int]]:
    """Map answer string to correct option indices"""
    if question_type == QuestionType.INTEGER:
        try:
            # For integer answers, try to extract numeric value
            # Handle cases like "3.37" -> 3 (for integer type, we might need to round)
            answer = float(gold)
            return int(round(answer)), None
        except:
            try:
                return int(gold), None
            except:
                return None, None
    
    elif question_type == QuestionType.MCQ:
        # Single answer: A=0, B=1, C=2, D=3
        if len(gold) == 1:
            return [ord(gold.upper()) - ord('A')], None
        return None, None
    
    elif question_type == QuestionType.SCQ:
        # Single correct answer: take first alpha character
        for char in gold:
            if char.isalpha():
                return None, ord(char.upper()) - ord('A')
        return None, None
    
    return None, None


async def get_or_create_class(db: AsyncSession, class_level: Class_level) -> Class:
    """Get existing class or create new one"""
    result = await db.execute(
        select(Class).where(Class.class_level == class_level)
    )
    class_obj = result.scalar_one_or_none()
    
    if not class_obj:
        from app.db.question_calls import create_class
        class_obj = await create_class(db, class_level)
    
    return class_obj


async def get_or_create_subject(
    db: AsyncSession,
    subject_type: Subject_Type,
    class_id: UUID
) -> Subject:
    """Get existing subject or create new one"""
    result = await db.execute(
        select(Subject).where(
            Subject.subject_type == subject_type,
            Subject.class_id == class_id
        )
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        from app.db.question_calls import create_subject
        subject = await create_subject(db, subject_type, class_id)
    
    return subject


async def get_or_create_chapter(
    db: AsyncSession,
    chapter_name: str,
    subject_id: UUID
) -> Chapter:
    """Get existing chapter or create new one"""
    result = await db.execute(
        select(Chapter).where(
            Chapter.name == chapter_name,
            Chapter.subject_id == subject_id
        )
    )
    chapter = result.scalar_one_or_none()
    
    if not chapter:
        from app.db.question_calls import create_chaps
        chapter = await create_chaps(db, subject_id, chapter_name)
    
    return chapter


async def get_or_create_topic(
    db: AsyncSession,
    topic_name: str,
    chapter_id: UUID
) -> Topic:
    """Get existing topic or create new one"""
    result = await db.execute(
        select(Topic).where(
            Topic.name == topic_name,
            Topic.chapter_id == chapter_id
        )
    )
    topic = result.scalar_one_or_none()
    
    if not topic:
        from app.db.question_calls import create_topic
        topic = await create_topic(db, chapter_id, topic_name)
    
    return topic


async def import_questions():
    """Main function to import questions from JSON data"""
    async with AsyncSessionLocal() as db:
        question_service = QuestionService(db)
        pyq_service = PYQService(db)
        
        # Use class 12 for all questions (JEE Advanced is typically class 12)
        class_obj = await get_or_create_class(db, Class_level.Twelth)
        
        stats = {
            "total": len(QUESTIONS_DATA),
            "created": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for idx, q_data in enumerate(QUESTIONS_DATA, 1):
            try:
                print(f"\n[{idx}/{stats['total']}] Processing question...")
                
                # Map subject
                subject_type = map_subject(q_data["subject"])
                subject = await get_or_create_subject(db, subject_type, class_obj.id)
                
                # Get or create chapter
                chapter_name = q_data.get("chapter", "General")
                chapter = await get_or_create_chapter(db, chapter_name, subject.id)
                
                # Get or create topic
                topic_name = q_data.get("topic", "General")
                topic = await get_or_create_topic(db, topic_name, chapter.id)
                
                # Map question type (pass gold answer for paragraph type detection)
                question_type = map_question_type(q_data["type"], q_data.get("gold"))
                
                # Extract exam type
                exam_types = extract_exam_type(q_data["description"])
                
                # Extract question text
                question_text = q_data["question"]
                
                # Extract options and answers based on type
                mcq_options = None
                mcq_correct_option = None
                scq_options = None
                scq_correct_options = None
                integer_answer = None
                
                if question_type == QuestionType.MCQ:
                    # Extract options from question text
                    options = extract_options_from_question(question_text)
                    if options:
                        mcq_options = options
                        # Map answer
                        mcq_correct_option, _ = map_answer_to_indices(q_data["gold"], question_type)
                    else:
                        print(f"  ⚠️  Warning: Could not extract options for MCQ question")
                        stats["skipped"] += 1
                        continue
                
                elif question_type == QuestionType.SCQ:
                    # Extract options from question text
                    options = extract_options_from_question(question_text)
                    if options:
                        scq_options = options
                        # Map multiple answers
                        _, scq_correct_options = map_answer_to_indices(q_data["gold"], question_type)
                        if scq_correct_options is None:
                            print(f"  ⚠️  Warning: Could not map SCQ answers")
                            stats["skipped"] += 1
                            continue
                    else:
                        print(f"  ⚠️  Warning: Could not extract options for SCQ question")
                        stats["skipped"] += 1
                        continue
                
                elif question_type == QuestionType.INTEGER:
                    # Extract integer answer
                    integer_answer, _ = map_answer_to_indices(q_data["gold"], question_type)
                    if integer_answer is None:
                        print(f"  ⚠️  Warning: Could not parse integer answer: {q_data['gold']}")
                        stats["skipped"] += 1
                        continue
                
                # Create question
                try:
                    question = await question_service.create_question(
                        topic_id=topic.id,
                        type=question_type,
                        difficulty=DifficultyLevel.MEDIUM,  # Default difficulty
                        exam_type=exam_types,
                        question_text=question_text,
                        marks=4,  # Default marks for JEE Advanced
                        solution_text="Solution not provided",  # Placeholder
                        question_image=None,
                        integer_answer=integer_answer,
                        mcq_options=mcq_options,
                        mcq_correct_option=mcq_correct_option,
                        scq_options=scq_options,
                        scq_correct_options=scq_correct_options,
                    )
                    
                    print(f"  ✓ Created question: {question.id}")
                    
                    # Create PYQ entry
                    exam_detail = [q_data["description"]]  # e.g., "JEE Adv 2016 Paper 1"
                    year = extract_year(q_data["description"])
                    pyq = await pyq_service.create_pyq(
                        question_id=question.id,
                        year=year,
                        exam_detail=exam_detail
                    )
                    
                    print(f"  ✓ Created PYQ entry: {pyq.id}")
                    stats["created"] += 1
                    
                except Exception as e:
                    print(f"  ✗ Error creating question: {str(e)}")
                    stats["errors"] += 1
                    continue
                    
            except Exception as e:
                print(f"  ✗ Error processing question {idx}: {str(e)}")
                stats["errors"] += 1
                continue
        
        # Print summary
        print("\n" + "="*50)
        print("IMPORT SUMMARY")
        print("="*50)
        print(f"Total questions: {stats['total']}")
        print(f"Successfully created: {stats['created']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print("="*50)


if __name__ == "__main__":
    print("Starting question import...")
    print("="*50)
    asyncio.run(import_questions())
    print("\nImport completed!")