# generate_config.py

import os
import json
import yaml
import sys

MARKER = "_END"

def remove_marker(secret_value):
    """如果 secret_value 以 MARKER 结尾，则去除它"""
    if secret_value and secret_value.endswith(MARKER):
        return secret_value[:-len(MARKER)]
    return secret_value

# 默认昵称的前缀
DEFAULT_NICKNAME_PREFIX = "未命名账号"

# 全局计数器，用于为未命名账号生成序号
unnamed_account_counter = 0

def get_next_default_nickname():
    """生成下一个带序号的默认昵称"""
    global unnamed_account_counter
    unnamed_account_counter += 1
    return f"{DEFAULT_NICKNAME_PREFIX}-{unnamed_account_counter}"

def load_and_merge_accounts():
    """
    从环境变量中加载并合并账号信息。
    如果 nickname 为空，则使用 "未命名账号-序号" 的格式。
    支持新旧两种 JSON 格式，以及独立的 Secrets。
    """
    global unnamed_account_counter # 声明要修改全局变量
    print("--- 开始加载并合并账号信息 ---")
    
    final_accounts = []
    seen_tokens = set()
    unnamed_account_counter = 0 # 每次运行时重置计数器

    # --- 1. 处理 SKLAND_ACCOUNTS_JSON ---
    json_str = os.environ.get('SKLAND_ACCOUNTS_JSON', '')

    if json_str:
        print("🔍 检测到 SKLAND_ACCOUNTS_JSON，正在尝试解析...")
        try:
            raw_data = json.loads(json_str)
            
            if not isinstance(raw_data, list):
                raise TypeError("JSON 根元素必须是一个数组。")

            # 尝试解析新格式: [{"nickname": "token"}]
            if all(isinstance(item, dict) and len(item) == 1 for item in raw_data):
                print("✅ 成功识别为新格式（简洁对象数组）。")
                for item in raw_data:
                    raw_nickname = list(item.keys())[0]
                    token = list(item.values())[0]
                    
                    # 如果原始昵称为空，则生成一个带序号的默认昵称
                    nickname = raw_nickname if raw_nickname else get_next_default_nickname()

                    if token and token not in seen_tokens:
                        final_accounts.append({'nickname': nickname, 'token': token})
                        seen_tokens.add(token)
                    elif not token:
                        print(f"⚠️ 警告: 新格式中发现一个 token 为空的账号，已跳过。")
                    else:
                        print(f"⚠️ 警告: 新格式中发现重复的 token，已跳过: {nickname}")
            
            # 尝试解析旧格式: [{"nickname": "...", "token": "..."}]
            elif all(isinstance(item, dict) and 'nickname' in item and 'token' in item for item in raw_data):
                print("✅ 成功识别为旧格式（标准对象数组）。")
                for item in raw_data:
                    token = item.get('token', '')
                    raw_nickname = item.get('nickname', '')

                    # 如果原始昵称为空，则生成一个带序号的默认昵称
                    nickname = raw_nickname if raw_nickname else get_next_default_nickname()

                    if token and token not in seen_tokens:
                        final_accounts.append({'nickname': nickname, 'token': token})
                        seen_tokens.add(token)
                    elif not token:
                        print(f"⚠️ 警告: 旧格式中发现一个 token 为空的账号，已跳过。")
                    else:
                        print(f"⚠️ 警告: 旧格式中发现重复的 token，已跳过: {nickname}")
            else:
                raise TypeError("JSON 列表格式不正确，既不是新格式也不是旧格式。")

            print(f"🎉 成功从 SKLAND_ACCOUNTS_JSON 加载了 {len(final_accounts)} 个唯一账号。")

        except json.JSONDecodeError as e:
            print(f"❌ 错误: SKLAND_ACCOUNTS_JSON 不是有效的 JSON 格式。错误: {e}")
            sys.exit(1)
        except (TypeError, ValueError) as e:
            print(f"❌ 错误: SKLAND_ACCOUNTS_JSON 格式不正确。错误: {e}")
            sys.exit(1)

    # --- 2. 处理 SKLAND_TOKEN 和 SKLAND_NICKNAME ---
    token = os.environ.get('SKLAND_TOKEN', '')
    nickname = remove_marker(os.environ.get('SKLAND_NICKNAME', '').strip())  # 去除前后空格

    if token:
        print("🔍 检测到独立 SKLAND_TOKEN，正在加载...")
        if token not in seen_tokens:
            # 如果独立配置的昵称为空，也使用带序号的默认昵称
            final_nickname = nickname if nickname else "未命名账号-独立"
            final_accounts.append({'nickname': final_nickname, 'token': token})
            seen_tokens.add(token)
            print("✅ 成功从独立 Secret 加载 1 个账号并完成合并。")
        else:
            print("⚠️ 警告: 独立 Secret 中的 token 与 JSON 配置中的账号重复，已跳过。")

    # --- 3. 最终检查 ---
    if not final_accounts:
        print("❌ 错误: 未找到任何有效的账号配置信息。")
        sys.exit(1)
        
    return final_accounts


def main():
    """主函数：合并账号并生成配置文件"""
    accounts = load_and_merge_accounts()
    
    # 按昵称排序
    accounts.sort(key=lambda x: x.get('nickname', ''))
    
    config = {
        'log_level': 'info',
        'users': accounts
    }

    try:
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        print(f"\n🎉 所有账号合并成功！共 {len(accounts)} 个。config.yaml 文件已生成。")
    except Exception as e:
        print(f"\n❌ 错误: 写入 config.yaml 文件时失败。错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()