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

# Initialize colorama for cross-platform colored output
colorama_init(autoreset=True)


class ScreenerApp:
    """Main application orchestrator for ScreenerIII"""

    def __init__(self):
        self.running = False
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

            self.logger.info(f"Database directory ready: {data_dir}")

        except Exception as e:
            self.logger.error(f"Unexpected error during database initialization: {e}")
            print(f"{Fore.RED}Database error: {e}{Style.RESET_ALL}")
            sys.exit(1)

    def initialize_components(self) -> None:
        """Initialize all application components"""
        try:
            self.logger.info("Initializing application components...")

            # Import required modules
            from src.data.oanda_client import OANDAClient
            from src.data.storage import StorageManager
            from src.interface.display import TerminalDisplay
            from config.markets import ALL_MARKET_SYMBOLS, MARKETS

            # Initialize OANDA API client
            self.oanda_client = OANDAClient(
                api_token=self.config['OANDA_API_KEY'],
                account_id=self.config['OANDA_ACCOUNT_ID'],
                environment=self.config['OANDA_ENVIRONMENT']
            )
            self.logger.info("OANDA client initialized")

            # Test OANDA connection
            if not self.oanda_client.test_connection():
                raise Exception("Failed to connect to OANDA API. Please check your credentials.")

            # Initialize storage manager
            db_path = Path(__file__).parent / 'data' / 'screener.db'
            self.storage = StorageManager(db_path=str(db_path))
            self.logger.info("Storage manager initialized")

            # Initialize terminal display
            self.display = TerminalDisplay(refresh_rate=self.config['UPDATE_INTERVAL'])
            self.logger.info("Terminal display initialized")

            # Store market symbols
            self.market_symbols = ALL_MARKET_SYMBOLS
            self.markets_config = MARKETS

            # Performance tracking
            self.stats = {
                'total_loops': 0,
                'successful_loops': 0,
                'failed_loops': 0,
                'total_errors': 0,
                'start_time': datetime.now()
            }

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

    def fetch_and_analyze_instrument(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time price and perform analysis for a single instrument.

        Args:
            symbol: Instrument symbol (e.g., 'XAU_USD')

        Returns:
            Dictionary with market data and analysis results, or None if failed
        """
        try:
            from src.data.market_data import Price, Candle
            from src.analysis.indicators import TechnicalIndicators
            from src.analysis.signals import SignalGenerator
            import pandas as pd

            # Fetch current price
            price_response = self.oanda_client.get_current_prices(symbol)

            if not price_response or 'prices' not in price_response:
                self.logger.warning(f"No price data received for {symbol}")
                return None

            price_data = price_response['prices'][0]
            price = Price.from_oanda_response(price_data)

            # Save price to database
            self.storage.save_price(price)

            # Fetch historical candles for technical analysis (last 200 5-minute candles)
            candles_response = self.oanda_client.get_candles(
                instrument=symbol,
                granularity='M5',
                count=200,
                price='M'
            )

            if not candles_response or 'candles' not in candles_response:
                self.logger.warning(f"No candle data received for {symbol}")
                return None

            # Convert candles to DataFrame
            candle_list = []
            for candle_data in candles_response['candles']:
                if candle_data.get('complete', False):
                    candle = Candle.from_oanda_response(symbol, candle_data, 'mid', 'M5')
                    candle_list.append(candle)

            # Save candles to database
            if candle_list:
                self.storage.save_candles(candle_list)

            # Create DataFrame for analysis
            df = pd.DataFrame([{
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume,
                'timestamp': c.timestamp
            } for c in candle_list])

            if df.empty or len(df) < 50:
                self.logger.warning(f"Insufficient candle data for {symbol}")
                return None

            df.set_index('timestamp', inplace=True)

            # Calculate technical indicators
            indicators = TechnicalIndicators(df)

            # Calculate key indicators
            rsi = indicators.calculate_rsi(14)
            atr = indicators.calculate_atr(14)
            trend = indicators.detect_trend()

            # Generate trading signal
            signal_generator = SignalGenerator(df, risk_percent=2.0)
            signal = signal_generator.generate_signal()

            # Calculate 24h change (compare current price to price 24h ago)
            # For 5-min candles, 24h = 288 candles
            change_24h = None
            if len(df) >= 288:
                price_24h_ago = df['close'].iloc[-288]
                change_24h = ((price.mid - price_24h_ago) / price_24h_ago) * 100
            elif len(df) >= 2:
                # Fallback: use oldest available data
                price_old = df['close'].iloc[0]
                change_24h = ((price.mid - price_old) / price_old) * 100

            # Prepare market data for display
            market_data = {
                'symbol': symbol,
                'price': price.mid,
                'bid': price.bid,
                'ask': price.ask,
                'spread': price.spread,
                'change_24h': change_24h,
                'signal': signal.signal_type.value,
                'direction': trend.get('direction', 'unknown'),
                'target': signal.target_1,
                'stop_loss': signal.stop_loss,
                'risk_reward': signal.risk_reward_ratio,
                'atr': atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0,
                'volume': candle_list[-1].volume if candle_list else 0,
                'confidence': signal.confidence,
                'timestamp': price.timestamp
            }

            return market_data

        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            self.stats['total_errors'] += 1
            return None

    def market_data_loop(self) -> None:
        """Main market data collection and display loop"""
        try:
            self.logger.info("Starting market data collection loop...")

            # Display startup banner
            self.display.display_startup_banner()

            iteration = 0

            while self.running:
                try:
                    iteration += 1
                    loop_start = time.time()
                    self.stats['total_loops'] += 1

                    self.logger.info(f"Loop iteration {iteration} started")

                    # Show loading message
                    self.display.display_loading(f"Fetching data for {len(self.market_symbols)} instruments...")

                    # Collect data for all instruments
                    market_data_list = []

                    for symbol in self.market_symbols:
                        try:
                            self.logger.debug(f"Processing {symbol}...")
                            data = self.fetch_and_analyze_instrument(symbol)

                            if data:
                                market_data_list.append(data)
                                self.logger.debug(f"Successfully processed {symbol}")
                            else:
                                self.logger.warning(f"Failed to process {symbol}")

                        except Exception as e:
                            self.logger.error(f"Error processing {symbol}: {e}")
                            self.stats['total_errors'] += 1
                            continue

                    # Display results if we have data
                    if market_data_list:
                        self.display.display_markets(market_data_list)
                        self.stats['successful_loops'] += 1
                        self.logger.info(f"Successfully displayed data for {len(market_data_list)} instruments")
                    else:
                        self.logger.warning("No market data to display")
                        self.stats['failed_loops'] += 1
                        print(f"\n{Fore.YELLOW}No market data available. Retrying...{Style.RESET_ALL}")

                    # Calculate loop performance
                    elapsed = time.time() - loop_start
                    self.logger.info(f"Loop {iteration} completed in {elapsed:.2f}s")

                    # Log performance stats every 10 iterations
                    if iteration % 10 == 0:
                        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
                        success_rate = (self.stats['successful_loops'] / self.stats['total_loops'] * 100) if self.stats['total_loops'] > 0 else 0
                        self.logger.info(
                            f"Performance: {self.stats['total_loops']} loops, "
                            f"{success_rate:.1f}% success rate, "
                            f"{self.stats['total_errors']} errors, "
                            f"{uptime/60:.1f}m uptime"
                        )

                    # Calculate sleep time to maintain consistent interval
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
                    self.stats['failed_loops'] += 1
                    self.stats['total_errors'] += 1
                    print(f"\n{Fore.RED}Error in data collection: {e}{Style.RESET_ALL}")
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

            # Close storage manager
            if hasattr(self, 'storage'):
                try:
                    self.storage.close()
                    self.logger.info("Storage manager closed")
                except Exception as e:
                    self.logger.error(f"Error closing storage manager: {e}")

            # Print final statistics
            if hasattr(self, 'stats'):
                uptime = (datetime.now() - self.stats['start_time']).total_seconds()
                success_rate = (self.stats['successful_loops'] / self.stats['total_loops'] * 100) if self.stats['total_loops'] > 0 else 0

                print(f"\n{Fore.CYAN}Session Statistics:{Style.RESET_ALL}")
                print(f"  Total loops: {self.stats['total_loops']}")
                print(f"  Successful: {self.stats['successful_loops']} ({success_rate:.1f}%)")
                print(f"  Failed: {self.stats['failed_loops']}")
                print(f"  Total errors: {self.stats['total_errors']}")
                print(f"  Uptime: {uptime/60:.1f} minutes")

                self.logger.info(
                    f"Session stats: {self.stats['total_loops']} loops, "
                    f"{success_rate:.1f}% success, "
                    f"{self.stats['total_errors']} errors, "
                    f"{uptime/60:.1f}m uptime"
                )

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
