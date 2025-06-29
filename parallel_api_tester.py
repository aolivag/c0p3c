#!/usr/bin/env python3
"""
GOOGLE PLACES API STRESS TESTER - EJECUCIÓN PARALELA
====================================================

Script para ejecutar múltiples consultas concurrentes a la API de Google Places
para evaluar límites de rate limiting y comportamiento bajo carga.

⚠️  SOLO PARA ANÁLISIS DE SEGURIDAD - USO AUTORIZADO
CLASIFICACIÓN: Evaluación de Vulnerabilidades - Personal Autorizado Copec
FECHA: Junio 2025
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict

class ParallelAPITester:
    """Clase para ejecutar pruebas paralelas de la API"""
    
    def __init__(self, num_workers=50):
        self.api_key = "AIzaSyAFTmmb51zsJYPdmbwJNckGH-nnwss9bD4"
        self.base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        self.num_workers = num_workers
        self.results = []
        self.lock = threading.Lock()
        
        # Consultas de prueba para variar las requests
        self.test_queries = [
            "copec",
            "restaurant santiago",
            "pharmacy chile",
            "bank santiago",
            "hospital chile",
            "shopping mall",
            "gas station",
            "coffee shop",
            "supermarket",
            "hotel santiago"
        ]
    
    def create_request_params(self, worker_id):
        """Crea parámetros para la request"""
        query = self.test_queries[worker_id % len(self.test_queries)]
        
        return {
            'query': query,
            'key': self.api_key,
            'location': "-33.4489,-70.6693",  # Santiago, Chile
            'radius': 50000,
            'language': 'es'
        }
    
    def single_api_call(self, worker_id):
        """Ejecuta una sola llamada a la API"""
        import requests
        
        params = self.create_request_params(worker_id)
        start_time = time.time()
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            end_time = time.time()
            
            result = {
                'worker_id': worker_id,
                'query': params['query'],
                'timestamp': datetime.now().isoformat(),
                'response_time_ms': round((end_time - start_time) * 1000, 2),
                'status_code': response.status_code,
                'success': False,
                'results_count': 0,
                'api_status': 'UNKNOWN',
                'error': None
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    api_status = data.get('status', 'UNKNOWN')
                    result['api_status'] = api_status
                    
                    if api_status == 'OK':
                        result['success'] = True
                        result['results_count'] = len(data.get('results', []))
                    elif api_status in ['REQUEST_DENIED', 'INVALID_REQUEST']:
                        result['error'] = data.get('error_message', 'API request denied')
                    elif api_status == 'OVER_QUERY_LIMIT':
                        result['error'] = 'Rate limit exceeded'
                    
                except json.JSONDecodeError:
                    result['error'] = 'Invalid JSON response'
            
            elif response.status_code == 403:
                result['error'] = 'Forbidden (403)'
            elif response.status_code == 429:
                result['error'] = 'Too Many Requests (429)'
            else:
                result['error'] = f'HTTP {response.status_code}'
            
            # Thread-safe append
            with self.lock:
                self.results.append(result)
                
            return result
            
        except Exception as e:
            error_result = {
                'worker_id': worker_id,
                'query': params['query'],
                'timestamp': datetime.now().isoformat(),
                'response_time_ms': 0,
                'status_code': 0,
                'success': False,
                'error': str(e)
            }
            
            with self.lock:
                self.results.append(error_result)
                
            return error_result
    
    def run_parallel_sync(self):
        """Ejecuta las pruebas en paralelo usando ThreadPoolExecutor"""
        print(f"🚀 INICIANDO {self.num_workers} WORKERS EN PARALELO (SYNC)")
        print("=" * 70)
        
        start_time = time.time()
        completed_workers = 0
        
        def worker_callback(future):
            nonlocal completed_workers
            completed_workers += 1
            result = future.result()
            status_icon = "✅" if result['success'] else "❌"
            print(f"{status_icon} Worker {result['worker_id']:2d}: {result['response_time_ms']:6.0f}ms | "
                  f"{result['query'][:15]:15s} | {result.get('api_status', 'ERROR')}")
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Enviar todas las tareas
            futures = []
            for i in range(self.num_workers):
                future = executor.submit(self.single_api_call, i + 1)
                future.add_done_callback(worker_callback)
                futures.append(future)
            
            # Esperar a que terminen todas
            for future in as_completed(futures):
                pass  # Los resultados se manejan en el callback
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print("\n" + "=" * 70)
        print(f"⏱️  TIEMPO TOTAL: {total_time:.2f} segundos")
        print(f"📊 REQUESTS POR SEGUNDO: {self.num_workers / total_time:.2f}")
        
        return self.analyze_results()
    
    async def single_api_call_async(self, session, worker_id):
        """Ejecuta una sola llamada asíncrona a la API"""
        params = self.create_request_params(worker_id)
        start_time = time.time()
        
        try:
            async with session.get(self.base_url, params=params, timeout=30) as response:
                end_time = time.time()
                
                result = {
                    'worker_id': worker_id,
                    'query': params['query'],
                    'timestamp': datetime.now().isoformat(),
                    'response_time_ms': round((end_time - start_time) * 1000, 2),
                    'status_code': response.status,
                    'success': False,
                    'results_count': 0,
                    'api_status': 'UNKNOWN',
                    'error': None
                }
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        api_status = data.get('status', 'UNKNOWN')
                        result['api_status'] = api_status
                        
                        if api_status == 'OK':
                            result['success'] = True
                            result['results_count'] = len(data.get('results', []))
                        elif api_status in ['REQUEST_DENIED', 'INVALID_REQUEST']:
                            result['error'] = data.get('error_message', 'API request denied')
                        elif api_status == 'OVER_QUERY_LIMIT':
                            result['error'] = 'Rate limit exceeded'
                        
                    except json.JSONDecodeError:
                        result['error'] = 'Invalid JSON response'
                
                elif response.status == 403:
                    result['error'] = 'Forbidden (403)'
                elif response.status == 429:
                    result['error'] = 'Too Many Requests (429)'
                else:
                    result['error'] = f'HTTP {response.status}'
                
                return result
                
        except Exception as e:
            return {
                'worker_id': worker_id,
                'query': params['query'],
                'timestamp': datetime.now().isoformat(),
                'response_time_ms': 0,
                'status_code': 0,
                'success': False,
                'error': str(e)
            }
    
    async def run_parallel_async(self):
        """Ejecuta las pruebas en paralelo usando asyncio"""
        print(f"🚀 INICIANDO {self.num_workers} WORKERS EN PARALELO (ASYNC)")
        print("=" * 70)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(self.num_workers):
                task = self.single_api_call_async(session, i + 1)
                tasks.append(task)
            
            # Ejecutar todas las tareas en paralelo
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados
            for result in results:
                if isinstance(result, Exception):
                    print(f"❌ Error: {result}")
                else:
                    status_icon = "✅" if result['success'] else "❌"
                    print(f"{status_icon} Worker {result['worker_id']:2d}: {result['response_time_ms']:6.0f}ms | "
                          f"{result['query'][:15]:15s} | {result.get('api_status', 'ERROR')}")
                    self.results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print("\n" + "=" * 70)
        print(f"⏱️  TIEMPO TOTAL: {total_time:.2f} segundos")
        print(f"📊 REQUESTS POR SEGUNDO: {self.num_workers / total_time:.2f}")
        
        return self.analyze_results()
    
    def analyze_results(self):
        """Analiza los resultados de las pruebas paralelas"""
        if not self.results:
            print("❌ No hay resultados para analizar")
            return None
        
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        
        # Estadísticas básicas
        total_requests = len(self.results)
        success_rate = len(successful) / total_requests * 100
        
        # Tiempos de respuesta
        response_times = [r['response_time_ms'] for r in successful]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Análisis de errores
        error_counts = defaultdict(int)
        for result in failed:
            error_type = result.get('error', 'Unknown error')
            error_counts[error_type] += 1
        
        # Estados de API
        api_status_counts = defaultdict(int)
        for result in self.results:
            status = result.get('api_status', 'UNKNOWN')
            api_status_counts[status] += 1
        
        # Costo estimado
        total_successful_requests = len(successful)
        estimated_cost = total_successful_requests * 0.017  # $17 per 1000 requests
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'test_config': {
                'workers': self.num_workers,
                'total_requests': total_requests
            },
            'success_metrics': {
                'successful_requests': len(successful),
                'failed_requests': len(failed),
                'success_rate_percent': round(success_rate, 2)
            },
            'performance_metrics': {
                'avg_response_time_ms': round(avg_response_time, 2),
                'min_response_time_ms': min_response_time,
                'max_response_time_ms': max_response_time
            },
            'error_analysis': dict(error_counts),
            'api_status_distribution': dict(api_status_counts),
            'cost_analysis': {
                'successful_requests': total_successful_requests,
                'estimated_cost_usd': round(estimated_cost, 4),
                'cost_per_request_usd': 0.017
            },
            'security_assessment': {
                'rate_limiting_detected': any('rate limit' in str(r.get('error', '')).lower() for r in failed),
                'api_restrictions_detected': any('403' in str(r.get('error', '')) for r in failed),
                'quota_exceeded': any('OVER_QUERY_LIMIT' in r.get('api_status', '') for r in self.results),
                'full_functionality': success_rate > 90
            }
        }
        
        self.print_analysis(analysis)
        return analysis
    
    def print_analysis(self, analysis):
        """Imprime el análisis de resultados"""
        print("\n🔍 ANÁLISIS DE RESULTADOS")
        print("=" * 70)
        
        # Métricas de éxito
        print(f"✅ Requests exitosos: {analysis['success_metrics']['successful_requests']}/{analysis['test_config']['total_requests']}")
        print(f"📊 Tasa de éxito: {analysis['success_metrics']['success_rate_percent']}%")
        
        # Performance
        perf = analysis['performance_metrics']
        print(f"⏱️  Tiempo promedio: {perf['avg_response_time_ms']}ms")
        print(f"⏱️  Tiempo mínimo: {perf['min_response_time_ms']}ms")
        print(f"⏱️  Tiempo máximo: {perf['max_response_time_ms']}ms")
        
        # Errores
        if analysis['error_analysis']:
            print(f"\n❌ ERRORES DETECTADOS:")
            for error, count in analysis['error_analysis'].items():
                print(f"   {error}: {count} veces")
        
        # Estados de API
        print(f"\n📊 DISTRIBUCIÓN DE ESTADOS:")
        for status, count in analysis['api_status_distribution'].items():
            print(f"   {status}: {count}")
        
        # Costo
        cost = analysis['cost_analysis']
        print(f"\n💰 IMPACTO ECONÓMICO:")
        print(f"   Requests exitosos: {cost['successful_requests']}")
        print(f"   Costo estimado: ${cost['estimated_cost_usd']} USD")
        
        # Seguridad
        sec = analysis['security_assessment']
        print(f"\n🔒 EVALUACIÓN DE SEGURIDAD:")
        print(f"   Rate limiting detectado: {'❌ NO' if not sec['rate_limiting_detected'] else '✅ SÍ'}")
        print(f"   Restricciones de API: {'❌ NO' if not sec['api_restrictions_detected'] else '✅ SÍ'}")
        print(f"   Cuota excedida: {'❌ NO' if not sec['quota_exceeded'] else '✅ SÍ'}")
        print(f"   Funcionalidad completa: {'🔴 SÍ' if sec['full_functionality'] else '✅ NO'}")
        
        if sec['full_functionality'] and not sec['rate_limiting_detected']:
            print(f"\n🚨 ALERTA CRÍTICA:")
            print(f"   🔴 API completamente funcional sin rate limiting")
            print(f"   🔴 Alto riesgo de abuso y costo económico")
            print(f"   🔴 Requiere acción inmediata")
    
    def save_detailed_report(self, analysis):
        """Guarda un reporte detallado en JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"parallel_api_test_report_{self.num_workers}workers_{timestamp}.json"
        
        detailed_report = {
            'analysis_summary': analysis,
            'detailed_results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Reporte detallado guardado en: {filename}")
        return filename

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Places API Parallel Tester')
    parser.add_argument('--workers', '-w', type=int, default=50, 
                       help='Número de workers paralelos (default: 50)')
    parser.add_argument('--async-mode', '-a', action='store_true',
                       help='Usar asyncio en lugar de threading')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔥 GOOGLE PLACES API PARALLEL STRESS TESTER")
    print("=" * 70)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👥 Workers: {args.workers}")
    async_mode = getattr(args, 'async_mode', False)
    print(f"🔧 Modo: {'Async (aiohttp)' if async_mode else 'Sync (ThreadPool)'}")
    print(f"🎯 Objetivo: Evaluar comportamiento bajo carga paralela")
    print()
    
    tester = ParallelAPITester(num_workers=args.workers)
    
    try:
        if async_mode:
            # Ejecutar en modo asíncrono
            analysis = asyncio.run(tester.run_parallel_async())
        else:
            # Ejecutar en modo síncrono con threads
            analysis = tester.run_parallel_sync()
        
        if analysis:
            tester.save_detailed_report(analysis)
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Prueba interrumpida por el usuario")
        if tester.results:
            print(f"📊 Resultados parciales: {len(tester.results)} requests completados")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
