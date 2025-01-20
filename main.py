import logging
from state_manager import StateManager
from controllers.cli_controller import CLIScrapeController
from arg_parser import create_argument_parser, get_scraper_args, handle_export_args

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    parser = create_argument_parser()
    args = parser.parse_args()
    setup_logging()
    logger = logging.getLogger(__name__)

    # Handle utility arguments
    if handle_export_args(args):
        return

    # Initialize state manager
    state_manager = StateManager(args.state if args.state else "scraper_state.json")
    
    # Handle resume logic
    if args.resume:
        if not state_manager.state:
            logger.error("No state file found to resume from")
            return
            
        saved_args = state_manager.get_scraper_args()
        scraper_args = {k: getattr(args, k) if getattr(args, k) != v else v 
                       for k, v in saved_args.items()}
        args.url = state_manager.state.url
        
    elif args.url:
        scraper_args = get_scraper_args(args)
        state_manager.initialize_state(args.url, **scraper_args)
    else:
        logger.error("Either --url or --resume must be specified")
        return

    # Start scraping
    controller = CLIScrapeController(state_manager)
    controller.start_scraping(args.url, scraper_args)

if __name__ == "__main__":
    main()
