from research_layer.crypto_autoresearch import run_crypto_7y_autoresearch


if __name__ == "__main__":
    report = run_crypto_7y_autoresearch()
    print("=== 7Y Crypto Autoresearch Complete ===")
    print(f"Report: {report['report_path']}")
    print("Best config:", report["autorresearch"]["best_config"])
    print("Summary:", report["summary"])
