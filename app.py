            for sent in doc['sentences']:
                sentence_words = [w['word'] for w in sent]
                sentence_text = ' '.join(sentence_words)
                sentence_lemmas_lower = [w['lemma'].lower() for w in sent]
                sentence_words_lower = [w['word'].lower() for w in sent]

                # Проверяем наличие всех слов из запроса
                all_present = True
                for qw in query_words:
                    found = False
                    for lemma, word in zip(sentence_lemmas_lower, sentence_words_lower):
                        if qw == lemma or qw == word or qw in word:   # ← главное изменение
                            found = True
                            break
                    if not found:
                        all_present = False
                        break

                if all_present:
                    # Подсветка
                    highlighted_sent = sentence_text
                    for ww in sent:
                        word_lower = ww['word'].lower()
                        lemma_lower = ww['lemma'].lower()
                        if any(qw == lemma_lower or qw == word_lower or qw in word_lower for qw in query_words):
                            highlighted_sent = re.sub(
                                r'\b' + re.escape(ww['word']) + r'\b',
                                f'<mark>{ww['word']}</mark>',
                                highlighted_sent,
                                flags=re.IGNORECASE
                            )

                    # Таблица только для найденных слов
                    table_rows = []
                    for token_idx, ww in enumerate(sent, 1):
                        word_lower = ww['word'].lower()
                        lemma_lower = ww['lemma'].lower()
                        if any(qw == lemma_lower or qw == word_lower or qw in word_lower for qw in query_words):
                            feats_kaz = translate_feats(ww['feats'], ww['lemma'])
                            deprel_kaz = translate_deprel(ww['deprel'])

                            table_rows.append({
                                'id': token_idx,
                                'word': ww['word'],
                                'lemma': ww['lemma'],
                                'upos': ww['pos'],
                                'feats_kaz': feats_kaz,
                                'deprel_kaz': deprel_kaz
                            })

                    if table_rows:
                        results.append({
                            'filename': filename,
                            'text_type': meta.get('text_type', 'Не указано'),
                            'level': meta.get('level', 'Не указано'),
                            'gender': meta.get('gender', 'Не указано'),
                            'publish_period': meta.get('publish_period', 'Не указано'),
                            'collect_date': meta.get('collect_date', 'Не указано'),
                            'word_count': meta.get('word_count', 'Не указано'),
                            'sentence': highlighted_sent,
                            'table_rows': table_rows
                        })
