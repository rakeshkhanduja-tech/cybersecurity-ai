"""VectorScope Command Line Interface"""

import argparse
import sys
import os
import json
from colorama import init, Fore, Style
from vectorscope.storage import VectorDatabase
from vectorscope.attacks.similarity_attack import SimilarityAttack
from vectorscope.attacks.reconstruction_attack import ReconstructionAttack
from vectorscope.attacks.pattern_attack import PatternRecognitionAttack

init(autoreset=True)

class VectorScopeCLI:
    def __init__(self):
        self.db = VectorDatabase()
        self.attacks = {
            'similarity': SimilarityAttack(self.db),
            'reconstruction': ReconstructionAttack(self.db),
            'pattern': PatternRecognitionAttack(self.db)
        }

    def run(self):
        parser = argparse.ArgumentParser(
            description=f"{Fore.CYAN}VectorScope: Vector Database Security Research Tool{Style.RESET_ALL}",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        subparsers = parser.add_subparsers(dest='command', help='Commands')

        # Store command
        store_parser = subparsers.add_parser('store', help='Store sensitive info into vector database')
        store_parser.add_argument('text', help='The sensitive text (e.g., "SSN: 123-45-6789")')
        store_parser.add_argument('--label', default='research_sample', help='Sample label')

        # Attack command
        attack_parser = subparsers.add_parser('attack', help='Run reverse engineering attacks')
        attack_parser.add_argument('--vector-id', help='Specific vector ID to attack (leave blank for latest)')
        attack_parser.add_argument('--type', choices=['ssn', 'creditcard'], default='ssn', help='Data type template')
        attack_parser.add_argument('--method', choices=['similarity', 'reconstruction', 'pattern', 'all'], default='all')

        # List command
        subparsers.add_parser('list', help='List stored vectors')
        
        # Clear command
        subparsers.add_parser('clear', help='Clear all stored vectors')

        args = parser.parse_args()

        if args.command == 'store':
            self._handle_store(args)
        elif args.command == 'attack':
            self._handle_attack(args)
        elif args.command == 'list':
            self._handle_list()
        elif args.command == 'clear':
            self.db.clear()
        else:
            parser.print_help()

    def _handle_store(self, args):
        print(f"\n{Fore.YELLOW}Storing sensitive information...{Style.RESET_ALL}")
        vid = self.db.store_text(args.text, {'label': args.label})
        print(f"{Fore.GREEN}[OK] Information stored successfully!{Style.RESET_ALL}")
        print(f"Vector ID: {Fore.CYAN}{vid}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Note: This info is now a 'black box' vector in the database.{Style.RESET_ALL}")

    def _handle_list(self):
        vectors = self.db.get_all_vectors()
        if not vectors:
            print(f"\n{Fore.RED}No vectors found in database.{Style.RESET_ALL}")
            return
            
        print(f"\n{Fore.CYAN}Stored Vectors:{Style.RESET_ALL}")
        for v in vectors:
            print(f"ID: {v['id']} | Label: {v['metadata'].get('label')} | Length: {v['metadata'].get('text_length')}")

    def _handle_attack(self, args):
        # Get target vector
        vid = args.vector_id
        target_vec = None
        ground_truth = "Unknown"

        vectors = self.db.get_all_vectors()
        if not vectors:
            print(f"{Fore.RED}Error: No vectors to attack.{Style.RESET_ALL}")
            return

        if not vid:
            # Use latest
            latest = vectors[-1]
            vid = latest['id']
            target_vec = latest['embedding']
            ground_truth = latest['metadata'].get('original_text', 'Unknown')
            print(f"Attacking latest vector: {Fore.CYAN}{vid}{Style.RESET_ALL}")
        else:
            # Find specific
            for v in vectors:
                if v['id'] == vid:
                    target_vec = v['embedding']
                    ground_truth = v['metadata'].get('original_text', 'Unknown')
                    break
            
            if target_vec is None:
                print(f"{Fore.RED}Error: Vector ID {vid} not found.{Style.RESET_ALL}")
                return

        print(f"\n{Fore.RED}=== INITIATING REVERSE ENGINEERING ATTACK ==={Style.RESET_ALL}")
        print(f"Target Vector ID: {vid}")
        print(f"Ground Truth Label: {ground_truth}") # For research validation
        print(f"Known format template: {args.type}")
        
        methods = ['similarity', 'reconstruction', 'pattern'] if args.method == 'all' else [args.method]
        
        for method in methods:
            print(f"\n{Fore.YELLOW}Executing {method} method...{Style.RESET_ALL}")
            attack_obj = self.attacks[method]
            result = attack_obj.execute(target_vec, data_type=args.type)
            
            print(result)
            
            # Evaluation
            eval_res = attack_obj.evaluate(result.extracted_text, ground_truth)
            if eval_res['exact_match']:
                print(f"{Fore.GREEN}CRITICAL: EXACT MATCH FOUND! Sensitive info leaked.{Style.RESET_ALL}")
            else:
                print(f"Partial Accuracy: {eval_res['partial_accuracy']:.2%}")
                
        print(f"\n{Fore.RED}=== ATTACK COMPLETED ==={Style.RESET_ALL}")

def main():
    cli = VectorScopeCLI()
    cli.run()

if __name__ == "__main__":
    main()
