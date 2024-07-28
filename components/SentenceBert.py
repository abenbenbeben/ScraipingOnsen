from transformers import BertJapaneseTokenizer, BertModel
import torch
import torch.nn.functional as F
import pandas as pd


class SentenceBertJapanese:
    def __init__(self, model_name_or_path, device=None):
        self.tokenizer = BertJapaneseTokenizer.from_pretrained(model_name_or_path)
        self.model = BertModel.from_pretrained(model_name_or_path)
        self.model.eval()

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model.to(device)

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0] #First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    @torch.no_grad()
    def encode(self, sentences, batch_size=8):
        all_embeddings = []
        iterator = range(0, len(sentences), batch_size)
        for batch_idx in iterator:
            batch = sentences[batch_idx:batch_idx + batch_size]

            encoded_input = self.tokenizer.batch_encode_plus(batch, padding="longest", 
                                           truncation=True, return_tensors="pt").to(self.device)
            model_output = self.model(**encoded_input)
            sentence_embeddings = self._mean_pooling(model_output, encoded_input["attention_mask"]).to('cpu')

            all_embeddings.extend(sentence_embeddings)

        # return torch.stack(all_embeddings).numpy()
        return torch.stack(all_embeddings)



def SentenceBertService(sentences):
    MODEL_NAME = "sonoisa/sentence-bert-base-ja-mean-tokens-v2"  # <- v2です。
    model = SentenceBertJapanese(MODEL_NAME)

    # sentences = ["暴走したAI", "暴走した人工知能"]
    sentence_embeddings = model.encode(sentences, batch_size=8)

    print("Sentence embeddings:", sentence_embeddings)

    # 最初の文に対するコサイン類似度を計算
    sim = F.cosine_similarity(sentence_embeddings[0].unsqueeze(0), sentence_embeddings).tolist()

    combined = [{'sim': s, 'sentence': sen} for s, sen in zip(sim, sentences)]

    # データフレームにまとめる
    df = pd.DataFrame({'文章': sentences, '類似度': sim})

    print(df)

    return combined

    






if __name__ == "__main__":
    sentences = ["サウナは無し", "サウナが温度が高くとても良い","サウナとミストサウナがめちゃくちゃ汗かける"]
    SentenceBertService(sentences)
