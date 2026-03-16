"""
Runner unificado — TechSupport Pro.
Ejecuta TODOS los tests: unitarios (Fase 2+3) + integración (Fase 4).

Uso:
    python run_tests.py           (todos)
    python run_tests.py --unit    (solo unitarios)
    python run_tests.py --integ   (solo integración)
"""
import sys, os, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

modo = sys.argv[1] if len(sys.argv) > 1 else "--all"

suite = unittest.TestSuite()
loader = unittest.TestLoader()

if modo in ("--all", "--unit"):
    from techsupportpro.tests.unit.use_cases.test_use_cases import (
        TestRegistrarCliente, TestLoginCliente, TestCrearTicket,
        TestActualizarTicket, TestCalificarTicket, TestMisTickets,
        TestCrearAlquiler, TestProcesarPago, TestDashboardAdmin,
    )
    for cls in [TestRegistrarCliente, TestLoginCliente, TestCrearTicket,
                TestActualizarTicket, TestCalificarTicket, TestMisTickets,
                TestCrearAlquiler, TestProcesarPago, TestDashboardAdmin]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

if modo in ("--all", "--integ"):
    from techsupportpro.tests.integration.test_integracion import (
        TestFlujoCompletoTicket, TestFlujoAlquiler,
        TestFlujoPago, TestDashboardIntegrado, TestModoJSON,
    )
    for cls in [TestFlujoCompletoTicket, TestFlujoAlquiler,
                TestFlujoPago, TestDashboardIntegrado, TestModoJSON]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

print("=" * 65)
print("  TechSupport Pro — Suite de Pruebas")
print(f"  Modo: {'Todos' if modo=='--all' else 'Unitarios' if modo=='--unit' else 'Integración'}")
print("=" * 65)

result = unittest.TextTestRunner(verbosity=2).run(suite)

print("=" * 65)
ok = result.wasSuccessful()
print(f"  {'✅ TODOS LOS TESTS PASAN' if ok else '❌ HAY FALLOS'}")
print(f"  Ejecutados: {result.testsRun} | "
      f"Errores: {len(result.errors)} | Fallos: {len(result.failures)}")
print("=" * 65)
sys.exit(0 if ok else 1)
