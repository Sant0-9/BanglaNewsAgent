import json
import re
import pickle
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import logging

# Lightweight ML libraries (fallback if sklearn not available)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.multioutput import MultiOutputClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, multilabel_confusion_matrix
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[ML] scikit-learn not available, using rule-based fallback only")

from packages.router.intent import INTENT_PATTERNS

class CompactIntentClassifier:
    """
    Compact multi-label intent classifier with rule-based fallback.
    Uses TF-IDF + Logistic Regression for speed and interpretability.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.intent_labels = ["news", "sports", "markets", "weather", "lookup"]
        self.model_path = model_path or "intent_classifier.pkl"
        self.vectorizer = None
        self.classifier = None
        self.is_trained = False
        self.training_stats = {}
        
        # Text preprocessing
        self.stop_words_en = {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 
            'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 
            'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 
            'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 
            'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 
            'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 
            'at', 'by', 'for', 'with', 'through', 'during', 'before', 'after', 'above', 
            'below', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 
            'further', 'then', 'once'
        }
        
        # Load model if exists
        if Path(self.model_path).exists():
            self.load_model()
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for feature extraction"""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove special characters but keep Bengali characters
        text = re.sub(r'[^\w\s\u0980-\u09FF]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def extract_features(self, queries: List[str]) -> np.ndarray:
        """Extract TF-IDF features from queries"""
        if not SKLEARN_AVAILABLE:
            # Simple bag-of-words features as fallback
            return self._extract_simple_features(queries)
        
        # Preprocess all queries
        processed_queries = [self.preprocess_text(q) for q in queries]
        
        if self.vectorizer is None:
            # Create vectorizer with optimized parameters for compact model
            self.vectorizer = TfidfVectorizer(
                max_features=1000,  # Compact feature space
                min_df=2,           # Ignore very rare terms
                max_df=0.8,         # Ignore very common terms  
                ngram_range=(1, 2), # Unigrams and bigrams
                sublinear_tf=True,  # Use log-scaled TF
                stop_words=None     # Keep all words for multilingual support
            )
            features = self.vectorizer.fit_transform(processed_queries)
        else:
            features = self.vectorizer.transform(processed_queries)
        
        return features.toarray()
    
    def _extract_simple_features(self, queries: List[str]) -> np.ndarray:
        """Simple feature extraction without sklearn"""
        # Create feature vocabulary from training patterns
        vocab = set()
        for intent_patterns in INTENT_PATTERNS.values():
            vocab.update(word.lower() for word in intent_patterns)
        
        vocab = sorted(list(vocab))
        features = []
        
        for query in queries:
            query_lower = query.lower()
            feature_vector = []
            
            for word in vocab:
                # Binary feature: word present or not
                feature_vector.append(1.0 if word in query_lower else 0.0)
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def train(self, training_file: str) -> Dict[str, Any]:
        """
        Train the multi-label intent classifier.
        
        Args:
            training_file: Path to JSON training data file
            
        Returns:
            Training statistics and performance metrics
        """
        print(f"[ML] Loading training data from {training_file}")
        
        with open(training_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        training_examples = data['training_data']
        queries = [example['query'] for example in training_examples]
        
        # Convert labels to multi-label binary matrix
        y_labels = []
        for example in training_examples:
            label_vector = []
            for intent in self.intent_labels:
                # Use threshold to convert continuous scores to binary labels
                threshold = 0.3  # Adjustable threshold
                label_vector.append(1 if example['labels'][intent] >= threshold else 0)
            y_labels.append(label_vector)
        
        y_labels = np.array(y_labels)
        
        print(f"[ML] Training on {len(queries)} queries with {len(self.intent_labels)} labels")
        
        # Extract features
        X_features = self.extract_features(queries)
        print(f"[ML] Feature matrix shape: {X_features.shape}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_features, y_labels, test_size=0.2, random_state=42, stratify=y_labels
        )
        
        if not SKLEARN_AVAILABLE:
            # Simple rule-based "training" - just store the patterns
            print("[ML] Using rule-based classification (sklearn not available)")
            self.is_trained = True
            self.training_stats = {
                "model_type": "rule_based",
                "training_samples": len(queries),
                "feature_count": X_features.shape[1],
                "trained_at": datetime.now(timezone.utc).isoformat()
            }
            return self.training_stats
        
        # Train multi-label classifier
        print("[ML] Training multi-label logistic regression...")
        
        self.classifier = MultiOutputClassifier(
            LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight='balanced'  # Handle class imbalance
            )
        )
        
        self.classifier.fit(X_train, y_train)
        
        # Evaluate on test set
        y_pred = self.classifier.predict(X_test)
        y_pred_proba = self.classifier.predict_proba(X_test)
        
        # Calculate per-label metrics
        label_metrics = {}
        for i, intent in enumerate(self.intent_labels):
            y_true_label = y_test[:, i]
            y_pred_label = y_pred[:, i]
            
            # Calculate precision, recall, F1
            tp = np.sum((y_true_label == 1) & (y_pred_label == 1))
            fp = np.sum((y_true_label == 0) & (y_pred_label == 1))
            fn = np.sum((y_true_label == 1) & (y_pred_label == 0))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            label_metrics[intent] = {
                "precision": precision,
                "recall": recall, 
                "f1": f1,
                "support": np.sum(y_true_label)
            }
        
        # Overall accuracy (exact match)
        exact_match_accuracy = np.mean(np.all(y_test == y_pred, axis=1))
        
        # Hamming loss (average per-label accuracy)
        hamming_accuracy = 1 - np.mean(y_test != y_pred)
        
        self.is_trained = True
        self.training_stats = {
            "model_type": "sklearn_logistic_regression",
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": X_features.shape[1],
            "exact_match_accuracy": exact_match_accuracy,
            "hamming_accuracy": hamming_accuracy,
            "label_metrics": label_metrics,
            "trained_at": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"[ML] Training complete!")
        print(f"  Exact match accuracy: {exact_match_accuracy:.3f}")
        print(f"  Hamming accuracy: {hamming_accuracy:.3f}")
        print(f"  Per-label F1 scores:")
        for intent, metrics in label_metrics.items():
            print(f"    {intent}: {metrics['f1']:.3f}")
        
        # Save model
        self.save_model()
        
        return self.training_stats
    
    def predict(self, query: str) -> Dict[str, Any]:
        """
        Predict intent(s) for a query.
        
        Args:
            query: Input query string
            
        Returns:
            Dict with primary intent, all scores, and confidence
        """
        if not self.is_trained:
            # Fall back to rule-based classification
            return self._predict_rule_based(query)
        
        if not SKLEARN_AVAILABLE or self.classifier is None:
            return self._predict_rule_based(query)
        
        # Extract features
        features = self.extract_features([query])
        
        # Get predictions and probabilities
        pred_binary = self.classifier.predict(features)[0]
        pred_probas = self.classifier.predict_proba(features)
        
        # Extract probabilities for positive class
        scores = {}
        for i, intent in enumerate(self.intent_labels):
            # Get probability of positive class (class 1)
            prob_positive = pred_probas[i][0][1] if pred_probas[i][0].shape[0] > 1 else pred_probas[i][0][0]
            scores[intent] = float(prob_positive)
        
        # Find primary intent (highest score)
        primary_intent = max(scores.items(), key=lambda x: x[1])[0]
        max_confidence = scores[primary_intent]
        
        # Check if multi-label
        active_intents = [intent for intent, score in scores.items() if score >= 0.3]
        is_multi_intent = len(active_intents) > 1
        
        return {
            "primary_intent": primary_intent,
            "confidence": max_confidence,
            "all_scores": scores,
            "is_multi_intent": is_multi_intent,
            "active_intents": active_intents,
            "model_used": "ml_classifier"
        }
    
    def _predict_rule_based(self, query: str) -> Dict[str, Any]:
        """Fallback rule-based prediction"""
        query_lower = query.lower().strip()
        scores = {intent: 0.0 for intent in self.intent_labels}
        
        for intent, keywords in INTENT_PATTERNS.items():
            if intent in self.intent_labels:
                score = 0.0
                for keyword in keywords:
                    if keyword.lower() in query_lower:
                        score += 0.2  # Each keyword adds 0.2
                
                scores[intent] = min(score, 1.0)  # Cap at 1.0
        
        primary_intent = max(scores.items(), key=lambda x: x[1])[0]
        max_confidence = scores[primary_intent]
        
        active_intents = [intent for intent, score in scores.items() if score >= 0.3]
        is_multi_intent = len(active_intents) > 1
        
        return {
            "primary_intent": primary_intent,
            "confidence": max_confidence,
            "all_scores": scores,
            "is_multi_intent": is_multi_intent,
            "active_intents": active_intents,
            "model_used": "rule_based_fallback"
        }
    
    def save_model(self):
        """Save trained model to disk"""
        if not self.is_trained:
            return
        
        model_data = {
            "vectorizer": self.vectorizer,
            "classifier": self.classifier,
            "intent_labels": self.intent_labels,
            "training_stats": self.training_stats,
            "is_trained": self.is_trained
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"[ML] Model saved to {self.model_path}")
    
    def load_model(self) -> bool:
        """Load trained model from disk"""
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.vectorizer = model_data['vectorizer']
            self.classifier = model_data['classifier']
            self.intent_labels = model_data['intent_labels']
            self.training_stats = model_data['training_stats']
            self.is_trained = model_data['is_trained']
            
            print(f"[ML] Model loaded from {self.model_path}")
            print(f"[ML] Model type: {self.training_stats.get('model_type', 'unknown')}")
            return True
            
        except Exception as e:
            print(f"[ML] Failed to load model: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and statistics"""
        return {
            "is_trained": self.is_trained,
            "model_path": self.model_path,
            "sklearn_available": SKLEARN_AVAILABLE,
            "training_stats": self.training_stats,
            "intent_labels": self.intent_labels
        }


def train_intent_classifier(training_data_file: str, model_output_path: str = None) -> CompactIntentClassifier:
    """
    Convenience function to train intent classifier.
    
    Args:
        training_data_file: Path to training data JSON file
        model_output_path: Optional path to save model
        
    Returns:
        Trained classifier instance
    """
    classifier = CompactIntentClassifier(model_output_path)
    stats = classifier.train(training_data_file)
    
    print(f"\n[ML] Training Summary:")
    print(f"  Model type: {stats.get('model_type', 'unknown')}")
    print(f"  Training samples: {stats.get('training_samples', 0)}")
    print(f"  Features: {stats.get('feature_count', 0)}")
    
    if 'hamming_accuracy' in stats:
        print(f"  Hamming accuracy: {stats['hamming_accuracy']:.3f}")
        print(f"  Best F1 scores:")
        for intent, metrics in stats['label_metrics'].items():
            print(f"    {intent}: {metrics['f1']:.3f}")
    
    return classifier