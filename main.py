#!/usr/bin/env python3
"""
ScreenerIII - Real-time Commodity Market Scanner
Main entry point for the application
"""

import sys
import os
import time
import signal
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Third-party imports
from dotenv import load_dotenv
from colorama import init as colorama_init, Fore, Style
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

# Initialize colorama for cross-platform colored output
colorama_init(autoreset=True)


class ScreenerApp:
    """Main application orchestrator for ScreenerIII"""

    def __init__(self):
        self.running = False
        self.db_session: Optional[Session] = None
        self.logger: Optional[logging.Logger] = None
        self.config: Dict[str, Any] = {}
        self.update_interval = 10  # seconds

    def setup_logging(self) -> None:
        """Initialize logging configuration"""
        try:
            # Ensure logs directory exists
            log_dir = Path(__file__).parent / 'logs'
            log_dir.mkdir(exist_ok=True)

            # Create log filename with timestamp
            log_file = log_dir / f'screener_{datetime.now().strftime("%Y%m%d")}.log'

            # Configure logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler(sys.stdout)
                ]
            )

            self.logger = logging.getLogger('ScreenerIII')
            self.logger.info("Logging initialized successfully")

        except Exception as e:
            print(f"{Fore.RED}Failed to initialize logging: {e}{Style.RESET_ALL}")
            sys.exit(1)

    def load_configuration(self) -> None:
        """Load configuration from .env file"""
        try:
            self.logger.info("Loading configuration...")

            # Check if .env file exists
            env_path = Path(__file__).parent / '.env'
            if not env_path.exists():
                self.logger.error(".env file not found")
                print(f"\n{Fore.RED}ERROR: .env file not found!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please create a .env file with the following variables:{Style.RESET_ALL}")
                print("  OANDA_API_KEY=your_api_key_here")
                print("  OANDA_ACCOUNT_ID=your_account_id_here")
                print("  OANDA_ENVIRONMENT=live")
                sys.exit(1)

            # Load environment variables
            load_dotenv(env_path)

            # Validate required environment variables
            required_vars = ['OANDA_API_KEY', 'OANDA_ACCOUNT_ID', 'OANDA_ENVIRONMENT']
            missing_vars = []

            for var in required_vars:
                value = os.getenv(var)
                if not value or value.strip() == '':
                    missing_vars.append(var)
                else:
                    self.config[var] = value

            if missing_vars:
                self.logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                print(f"\n{Fore.RED}ERROR: Missing required environment variables!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}The following variables are missing or empty in .env:{Style.RESET_ALL}")
                for var in missing_vars:
                    print(f"  - {var}")
                sys.exit(1)

            # Validate OANDA_ENVIRONMENT value
            valid_environments = ['live', 'practice']
            if self.config['OANDA_ENVIRONMENT'].lower() not in valid_environments:
                self.logger.error(f"Invalid OANDA_ENVIRONMENT: {self.config['OANDA_ENVIRONMENT']}")
                print(f"\n{Fore.RED}ERROR: Invalid OANDA_ENVIRONMENT!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}OANDA_ENVIRONMENT must be either 'live' or 'practice'{Style.RESET_ALL}")
                sys.exit(1)

            # Load optional configuration with defaults
            self.config['UPDATE_INTERVAL'] = int(os.getenv('UPDATE_INTERVAL', '10'))
            self.config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')

            # Update log level if specified
            if self.config['LOG_LEVEL']:
                self.logger.setLevel(getattr(logging, self.config['LOG_LEVEL'].upper(), logging.INFO))

            self.logger.info("Configuration loaded successfully")
            self.logger.info(f"Environment: {self.config['OANDA_ENVIRONMENT']}")
            self.logger.info(f"Update interval: {self.config['UPDATE_INTERVAL']} seconds")

        except ValueError as e:
            self.logger.error(f"Configuration value error: {e}")
            print(f"{Fore.RED}Configuration error: {e}{Style.RESET_ALL}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            print(f"{Fore.RED}Failed to load configuration: {e}{Style.RESET_ALL}")
            sys.exit(1)

    def initialize_database(self) -> None:
        """Initialize database connection and create tables"""
        try:
            self.logger.info("Initializing database...")

            # Ensure data directory exists
            data_dir = Path(__file__).parent / 'data'
            data_dir.mkdir(exist_ok=True)

            # Create database path
            db_path = data_dir / 'screener.db'
            db_url = f'sqlite:///{db_path}'

            # Create engine
            engine = create_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                connect_args={'check_same_thread': False}
            )

            # Create session factory
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            self.db_session = SessionLocal()

            # TODO: Import and create database tables when models are available
            # from src.data.models import Base
            # Base.metadata.create_all(bind=engine)

            self.logger.info(f"Database initialized: {db_path}")

        except SQLAlchemyError as e:
            self.logger.error(f"Database initialization failed: {e}")
            print(f"{Fore.RED}Database initialization failed: {e}{Style.RESET_ALL}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error during database initialization: {e}")
            print(f"{Fore.RED}Database error: {e}{Style.RESET_ALL}")
            sys.exit(1)

    def initialize_components(self) -> None:
        """Initialize all application components"""
        try:
            self.logger.info("Initializing application components...")

            # TODO: Initialize OANDA API client when available
            # from src.data.oanda_client import OandaClient
            # self.oanda_client = OandaClient(
            #     api_key=self.config['OANDA_API_KEY'],
            #     account_id=self.config['OANDA_ACCOUNT_ID'],
            #     environment=self.config['OANDA_ENVIRONMENT']
            # )

            # TODO: Initialize market data collector when available
            # from src.core.data_collector import DataCollector
            # self.data_collector = DataCollector(
            #     oanda_client=self.oanda_client,
            #     db_session=self.db_session
            # )

            # TODO: Initialize technical analysis engine when available
            # from src.analysis.technical_analyzer import TechnicalAnalyzer
            # self.technical_analyzer = TechnicalAnalyzer()

            # TODO: Initialize pattern recognition when available
            # from src.analysis.pattern_recognition import PatternRecognizer
            # self.pattern_recognizer = PatternRecognizer()

            # TODO: Initialize dashboard interface when available
            # from src.interface.dashboard import Dashboard
            # self.dashboard = Dashboard()

            self.logger.info("All components initialized successfully")

        except ImportError as e:
            self.logger.error(f"Failed to import required module: {e}")
            print(f"{Fore.RED}Component initialization failed: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Some modules may not be implemented yet.{Style.RESET_ALL}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Component initialization error: {e}")
            print(f"{Fore.RED}Failed to initialize components: {e}{Style.RESET_ALL}")
            sys.exit(1)

    def display_startup_banner(self) -> None:
        """Display startup banner and status"""
        banner = f"""
{Fore.CYAN}{'=' * 80}
{Fore.GREEN}  ScreenerIII - Real-time Commodity Market Scanner
{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}

{Fore.YELLOW}Status:{Style.RESET_ALL} Starting...
{Fore.YELLOW}Environment:{Style.RESET_ALL} {self.config.get('OANDA_ENVIRONMENT', 'N/A')}
{Fore.YELLOW}Update Interval:{Style.RESET_ALL} {self.config.get('UPDATE_INTERVAL', 10)} seconds
{Fore.YELLOW}Database:{Style.RESET_ALL} Connected
{Fore.YELLOW}Time:{Style.RESET_ALL} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}

{Fore.GREEN}Press Ctrl+C to stop the scanner{Style.RESET_ALL}
"""
        print(banner)

    def market_data_loop(self) -> None:
        """Main market data collection and display loop"""
        try:
            self.logger.info("Starting market data collection loop...")
            iteration = 0

            while self.running:
                try:
                    iteration += 1
                    loop_start = time.time()

                    self.logger.debug(f"Loop iteration {iteration} started")

                    # TODO: Collect market data when data collector is available
                    # market_data = self.data_collector.collect_all_instruments()

                    # TODO: Perform technical analysis when analyzer is available
                    # analysis_results = self.technical_analyzer.analyze(market_data)

                    # TODO: Detect patterns when pattern recognizer is available
                    # patterns = self.pattern_recognizer.detect_patterns(market_data)

                    # TODO: Update dashboard display when dashboard is available
                    # self.dashboard.update(market_data, analysis_results, patterns)

                    # Placeholder display
                    print(f"\n{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}]{Style.RESET_ALL} "
                          f"Iteration {iteration} - Collecting market data...")

                    # Calculate sleep time to maintain consistent interval
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, self.config.get('UPDATE_INTERVAL', 10) - elapsed)

                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    else:
                        self.logger.warning(f"Loop iteration took longer than update interval: {elapsed:.2f}s")

                except KeyboardInterrupt:
                    # Re-raise to be caught by outer handler
                    raise
                except Exception as e:
                    self.logger.error(f"Error in market data loop iteration {iteration}: {e}", exc_info=True)
                    print(f"{Fore.RED}Error in data collection: {e}{Style.RESET_ALL}")
                    # Continue running despite errors
                    time.sleep(5)  # Brief pause before retry

        except KeyboardInterrupt:
            self.logger.info("Market data loop interrupted by user")
        except Exception as e:
            self.logger.error(f"Fatal error in market data loop: {e}", exc_info=True)
            print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")

    def shutdown(self) -> None:
        """Graceful shutdown of all components"""
        try:
            self.logger.info("Initiating graceful shutdown...")
            print(f"\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")

            self.running = False

            # Close database session
            if self.db_session:
                try:
                    self.db_session.close()
                    self.logger.info("Database session closed")
                except Exception as e:
                    self.logger.error(f"Error closing database session: {e}")

            # TODO: Close OANDA API connections when available
            # if hasattr(self, 'oanda_client'):
            #     self.oanda_client.close()

            # TODO: Save any pending data or state

            self.logger.info("Shutdown complete")
            print(f"{Fore.GREEN}Shutdown complete. Goodbye!{Style.RESET_ALL}")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
            print(f"{Fore.RED}Error during shutdown: {e}{Style.RESET_ALL}")

    def signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        signal_names = {
            signal.SIGINT: 'SIGINT',
            signal.SIGTERM: 'SIGTERM'
        }
        signal_name = signal_names.get(signum, f'Signal {signum}')

        self.logger.info(f"Received {signal_name}, initiating shutdown...")
        print(f"\n{Fore.YELLOW}Received {signal_name}...{Style.RESET_ALL}")

        self.running = False

    def run(self) -> int:
        """Main application run method"""
        try:
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            # Initialize application
            self.setup_logging()
            self.load_configuration()
            self.initialize_database()
            self.initialize_components()

            # Display startup information
            self.display_startup_banner()

            # Set running flag
            self.running = True

            # Start main loop
            self.market_data_loop()

            # Normal shutdown
            self.shutdown()
            return 0

        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
            self.shutdown()
            return 0
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fatal application error: {e}", exc_info=True)
            print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
            return 1


def main():
    """Entry point for the application"""
    app = ScreenerApp()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
