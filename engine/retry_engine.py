"""
Smart Retry Engine for SurgiInject
Handles AI failures with intelligent escalation and prompt correction
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime

from .response_validator import validator, is_weak_response, log_failure, auto_correct_prompt, get_optimal_provider_chain
from .injection_queue import add_injection_result

logger = logging.getLogger(__name__)


class RetryEngine:
    """Smart retry engine for AI injection failures"""
    
    def __init__(self, max_attempts: int = 3, max_providers: int = 3):
        self.max_attempts = max_attempts
        self.max_providers = max_providers
        self.validator = validator  # Add validator attribute for tests
    
    def inject_with_retry(self, 
                         file_path: str, 
                         prompt: str, 
                         query_model_func,
                         provider_chain: Optional[List[str]] = None,
                         **kwargs) -> str:
        """
        Inject with smart retry logic.
        
        Args:
            file_path: Path to the file being processed
            prompt: Original prompt
            query_model_func: Function to query AI model
            provider_chain: Optional list of providers to try
            **kwargs: Additional arguments for query_model_func
            
        Returns:
            Successful AI response
            
        Raises:
            RuntimeError: If all attempts fail
        """
        if provider_chain is None:
            provider_chain = get_optimal_provider_chain(file_path, prompt)
        
        # Limit provider chain
        provider_chain = provider_chain[:self.max_providers]
        
        logger.info(f"Starting injection with retry for {file_path}")
        logger.info(f"Provider chain: {provider_chain}")
        
        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Attempt {attempt}/{self.max_attempts}")
            
            # Auto-correct prompt for retry attempts
            current_prompt = prompt
            if attempt > 1:
                current_prompt = auto_correct_prompt(prompt, attempt)
                logger.info(f"Auto-corrected prompt for attempt {attempt}")
            
            # Try each provider in the chain
            for provider in provider_chain:
                try:
                    logger.info(f"Trying provider: {provider}")
                    
                    # Check if this is a duplicate failure
                    if validator.is_duplicate_failure(file_path, current_prompt, provider):
                        logger.warning(f"Skipping {provider} due to previous failure")
                        continue
                    
                    # Query the model
                    # Remove provider from kwargs to avoid conflict
                    call_kwargs = kwargs.copy()
                    call_kwargs.pop('provider', None)
                    
                    response = query_model_func(
                        prompt=current_prompt,
                        provider=provider,
                        **call_kwargs
                    )
                    
                    # Validate the response
                    if is_weak_response(response):
                        try:
                            log_failure(file_path, current_prompt, provider, "Weak response")
                        except Exception as e:
                            logger.warning(f"Failed to log failure: {e}")
                        logger.warning(f"⚠️ Weak response from {provider}, trying next provider...")
                        continue
                    
                    # Success!
                    logger.info(f"✅ Successful injection with {provider} on attempt {attempt}")
                    return response
                    
                except Exception as e:
                    error_msg = str(e)
                    try:
                        log_failure(file_path, current_prompt, provider, error_msg)
                    except Exception as log_error:
                        logger.warning(f"Failed to log failure: {log_error}")
                    logger.error(f"❌ Error from {provider}: {error_msg}")
                    continue
            
            # If we get here, all providers failed for this attempt
            logger.warning(f"All providers failed for attempt {attempt}")
        
        # All attempts failed
        error_msg = f"🚨 All {self.max_attempts} attempts failed for {file_path}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def inject_with_fallback(self, 
                           file_path: str, 
                           prompt: str, 
                           query_model_func,
                           fallback_content: Optional[str] = None,
                           **kwargs) -> str:
        """
        Inject with fallback content if all AI attempts fail.
        
        Args:
            file_path: Path to the file being processed
            prompt: Original prompt
            query_model_func: Function to query AI model
            fallback_content: Content to return if all AI attempts fail
            **kwargs: Additional arguments for query_model_func
            
        Returns:
            AI response or fallback content
        """
        try:
            return self.inject_with_retry(file_path, prompt, query_model_func, **kwargs)
        except RuntimeError as e:
            logger.warning(f"All AI attempts failed, using fallback: {e}")
            
            if fallback_content:
                return fallback_content
            else:
                # Return a minimal fallback
                return f"# AI injection failed for {Path(file_path).name}\n# Original prompt: {prompt[:100]}...\n# Please try again or check your prompt."
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get retry statistics.
        
        Returns:
            Dictionary with retry statistics
        """
        failure_stats = validator.get_failure_stats()
        
        return {
            "max_attempts": self.max_attempts,
            "max_providers": self.max_providers,
            "failure_stats": failure_stats,
            "total_failures": failure_stats.get("total_failures", 0),
            "providers": failure_stats.get("providers", {}),
            "files": failure_stats.get("files", {}),
            "recent_failures": failure_stats.get("recent_failures", [])
        }
    
    def clear_failure_log(self) -> None:
        """Clear the failure log."""
        if validator.failure_log_path.exists():
            validator.failure_log_path.unlink()
            logger.info("Failure log cleared")
    
    def export_failure_report(self, output_path: str) -> None:
        """
        Export failure report to file.
        
        Args:
            output_path: Path to save the report
        """
        stats = self.get_retry_stats()
        
        report = {
            "generated_at": str(datetime.now()),
            "retry_engine_config": {
                "max_attempts": self.max_attempts,
                "max_providers": self.max_providers
            },
            "statistics": stats,
            "recommendations": self._generate_recommendations(stats)
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Failure report exported to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export failure report: {e}")
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """Generate recommendations based on failure statistics."""
        recommendations = []
        
        total_failures = stats.get("total_failures", 0)
        if total_failures == 0:
            recommendations.append("No failures recorded - system is working well!")
            return recommendations
        
        # Provider-specific recommendations
        providers = stats.get("providers", {})
        if providers:
            worst_provider = max(providers.items(), key=lambda x: x[1])
            recommendations.append(f"Provider '{worst_provider[0]}' has the most failures ({worst_provider[1]}). Consider adjusting its configuration.")
        
        # File-specific recommendations
        files = stats.get("files", {})
        if files:
            worst_file = max(files.items(), key=lambda x: x[1])
            recommendations.append(f"File '{worst_file[0]}' has the most failures ({worst_file[1]}). Consider reviewing prompts for this file type.")
        
        # General recommendations
        if total_failures > 10:
            recommendations.append("High failure rate detected. Consider reviewing prompt templates and provider configurations.")
        
        if total_failures > 50:
            recommendations.append("Very high failure rate. Consider implementing prompt optimization or switching providers.")
        
        return recommendations


# Global retry engine instance
retry_engine = RetryEngine()


def inject_with_retry(file_path: str, 
                     prompt: str, 
                     query_model_func,
                     provider_chain: Optional[List[str]] = None,
                     **kwargs) -> str:
    """Convenience function for injection with retry."""
    # Read original content for queue
    original_content = ""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        logger.warning(f"Could not read original content for queue: {e}")
    
    # Run injection with retry
    result = retry_engine.inject_with_retry(file_path, prompt, query_model_func, provider_chain, **kwargs)
    
    # Add to injection queue for dashboard preview
    try:
        # Determine status based on response quality
        status = "success"
        if is_weak_response(result):
            status = "weak"
        
        # Determine provider (simplified - could be enhanced)
        provider = "retry-engine"
        if provider_chain and len(provider_chain) > 0:
            provider = provider_chain[0]
        
        add_injection_result(
            file_path=file_path,
            original_content=original_content,
            injected_content=result,
            status=status,
            provider=provider,
            with_context=False  # Single file injections don't use context
        )
    except Exception as e:
        logger.warning(f"Failed to add injection result to queue: {e}")
    
    return result


def inject_with_fallback(file_path: str, 
                        prompt: str, 
                        query_model_func,
                        fallback_content: Optional[str] = None,
                        **kwargs) -> str:
    """Convenience function for injection with fallback."""
    return retry_engine.inject_with_fallback(file_path, prompt, query_model_func, fallback_content, **kwargs)


def get_retry_stats() -> Dict[str, Any]:
    """Convenience function to get retry statistics."""
    return retry_engine.get_retry_stats() 