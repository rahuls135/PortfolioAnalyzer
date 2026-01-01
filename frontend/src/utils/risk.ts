export type RiskTolerance = 'conservative' | 'moderate' | 'aggressive';

interface RiskInputs {
  age: number;
  income: number;
  retirementYears: number;
  obligationsAmount?: number;
}

export function computeRiskRecommendation({
  age,
  income,
  retirementYears,
  obligationsAmount = 0
}: RiskInputs): RiskTolerance {
  const highObligations = obligationsAmount >= 2500;
  const lowObligations = obligationsAmount <= 1000;

  if (retirementYears <= 10 || age >= 55 || highObligations) {
    return 'conservative';
  }

  if (retirementYears >= 25 && income >= 100000 && lowObligations) {
    return 'aggressive';
  }

  return 'moderate';
}
